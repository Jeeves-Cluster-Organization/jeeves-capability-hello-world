mod tools;
mod knowledge;

use std::sync::Arc;

use axum::extract::State;
use axum::response::sse::{Event, Sse};
use axum::response::Html;
use axum::routing::{get, post};
use axum::{Json, Router};
use serde::Deserialize;
use tokio_stream::wrappers::ReceiverStream;
use tracing::info;

use jeeves_core::prelude::*;
use jeeves_core::worker::llm::genai_provider::GenaiProvider;

#[derive(Clone)]
struct AppState {
    handle: KernelHandle,
    agents: Arc<AgentRegistry>,
    config: PipelineConfig,
}

#[derive(Deserialize)]
struct ChatRequest {
    message: String,
    #[serde(default = "default_user")]
    user_id: String,
}

fn default_user() -> String {
    "user".into()
}

#[tokio::main]
async fn main() {
    let _ = dotenvy::dotenv();
    tracing_subscriber::fmt()
        .with_env_filter(std::env::var("LOG_LEVEL").unwrap_or_else(|_| "info".into()))
        .init();

    let model = std::env::var("OPENAI_MODEL").unwrap_or_else(|_| "gpt-4o-mini".into());
    let port: u16 = std::env::var("PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(8001);

    // Load pipeline
    let config: PipelineConfig = serde_json::from_str(
        &std::fs::read_to_string("pipeline.json").expect("pipeline.json not found"),
    )
    .expect("invalid pipeline.json");

    // Kernel
    let kernel = Kernel::new();
    let cancel = tokio_util::sync::CancellationToken::new();
    let handle = spawn_kernel(kernel, cancel);

    // LLM + prompts
    let llm: Arc<dyn LlmProvider> = Arc::new(GenaiProvider::new(&model));
    let prompts = Arc::new(PromptRegistry::from_dir("prompts"));

    // Tools
    let tool_registry = ToolRegistryBuilder::new()
        .add_executor(Arc::new(tools::HelloWorldTools::new()))
        .build();

    // Build agents from pipeline stages
    let agents = AgentFactoryBuilder::new(llm, prompts, tool_registry, handle.clone())
        .add_pipeline(config.clone())
        .build();

    let state = AppState {
        handle,
        agents,
        config,
    };

    let app = Router::new()
        .route("/", get(index))
        .route("/chat", post(chat))
        .route("/chat/stream", post(chat_stream))
        .route("/health", get(|| async { "OK" }))
        .with_state(state);

    let addr = format!("0.0.0.0:{}", port);
    let listener = tokio::net::TcpListener::bind(&addr).await.unwrap();
    info!(addr = %addr, "hello-world listening");
    axum::serve(listener, app).await.unwrap();
}

async fn index() -> Html<&'static str> {
    Html(include_str!("../chat.html"))
}

async fn chat(State(state): State<AppState>, Json(req): Json<ChatRequest>) -> Json<serde_json::Value> {
    let session_id = format!("sess_{}", uuid::Uuid::new_v4().simple());
    let envelope = Envelope::new_minimal(&req.user_id, &session_id, &req.message, None);
    let pid = ProcessId::new();
    match run_pipeline_with_envelope(&state.handle, pid, state.config.clone(), envelope, &state.agents)
        .await
    {
        Ok(result) => {
            let respond = result.outputs.get("respond").cloned().unwrap_or_default();
            let response = respond
                .get("response")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            Json(serde_json::json!({"response": response}))
        }
        Err(e) => Json(serde_json::json!({"error": e.to_string()})),
    }
}

async fn chat_stream(
    State(state): State<AppState>,
    Json(req): Json<ChatRequest>,
) -> Sse<impl tokio_stream::Stream<Item = Result<Event, std::convert::Infallible>>> {
    let session_id = format!("sess_{}", uuid::Uuid::new_v4().simple());
    let envelope = Envelope::new_minimal(&req.user_id, &session_id, &req.message, None);
    let pid = ProcessId::new();

    let (tx, rx) = tokio::sync::mpsc::channel::<Result<Event, std::convert::Infallible>>(32);

    tokio::spawn(async move {
        match run_pipeline_streaming(
            state.handle,
            pid,
            state.config,
            envelope,
            state.agents,
        )
        .await
        {
            Ok((_handle, mut event_rx)) => {
                while let Some(event) = event_rx.recv().await {
                    let sse = match &event {
                        PipelineEvent::Delta { content, .. } => {
                            Event::default().data(content.clone())
                        }
                        PipelineEvent::Done { .. } => {
                            Event::default().event("done").data("")
                        }
                        _ => continue,
                    };
                    if tx.send(Ok(sse)).await.is_err() {
                        break;
                    }
                }
            }
            Err(e) => {
                let _ = tx
                    .send(Ok(Event::default().event("error").data(e.to_string())))
                    .await;
            }
        }
    });

    Sse::new(ReceiverStream::new(rx))
}

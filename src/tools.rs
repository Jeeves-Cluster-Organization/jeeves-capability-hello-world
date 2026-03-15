use std::collections::HashMap;
use async_trait::async_trait;
use serde_json::{json, Value};
use jeeves_core::worker::tools::{ToolExecutor, ToolInfo};
use crate::knowledge;

#[derive(Debug)]
pub struct HelloWorldTools {
    section_map: HashMap<String, Vec<String>>,
}

impl HelloWorldTools {
    pub fn new() -> Self {
        let mut section_map = HashMap::new();
        section_map.insert("architecture".into(), vec!["ecosystem_overview".into(), "layer_details".into()]);
        section_map.insert("concept".into(), vec!["key_concepts".into(), "code_examples".into()]);
        section_map.insert("getting_started".into(), vec!["hello_world_structure".into(), "how_to_guides".into()]);
        section_map.insert("component".into(), vec!["ecosystem_overview".into(), "layer_details".into()]);
        section_map.insert("general".into(), vec!["ecosystem_overview".into()]);
        Self { section_map }
    }
}

#[async_trait]
impl ToolExecutor for HelloWorldTools {
    async fn execute(&self, name: &str, params: Value) -> jeeves_core::Result<Value> {
        match name {
            "get_time" => {
                let now = chrono::Utc::now();
                Ok(json!({
                    "status": "success",
                    "datetime": now.format("%Y-%m-%d %H:%M:%S").to_string(),
                    "date": now.format("%Y-%m-%d").to_string(),
                    "time": now.format("%H:%M:%S").to_string(),
                    "timezone": "UTC",
                    "day_of_week": now.format("%A").to_string(),
                    "iso_format": now.to_rfc3339(),
                }))
            }
            "list_tools" => {
                Ok(json!({
                    "status": "success",
                    "tools": [
                        {
                            "id": "get_time",
                            "description": "Get the current date and time (UTC)",
                            "parameters": {},
                            "examples": ["What time is it?", "What's today's date?"]
                        },
                        {
                            "id": "list_tools",
                            "description": "List all available tools and capabilities",
                            "parameters": {},
                            "examples": ["What can you do?", "What tools do you have?"]
                        }
                    ],
                    "capabilities": [
                        "Explain the Jeeves ecosystem architecture (3 layers)",
                        "Describe jeeves-core (Rust micro-kernel)",
                        "Explain key concepts: Envelope, PipelineConfig, routing",
                        "Explain the multi-agent pipeline pattern",
                        "Help with getting started and adding tools"
                    ],
                    "count": 2
                }))
            }
            "think_knowledge" => {
                let intent = params.get("outputs")
                    .and_then(|o| o.get("understand"))
                    .and_then(|u| u.get("intent"))
                    .and_then(|v| v.as_str())
                    .unwrap_or("general");
                let sections = self.section_map.get(intent)
                    .cloned()
                    .unwrap_or_else(|| vec!["ecosystem_overview".into()]);
                let targeted = knowledge::get_for_sections(&sections);
                Ok(json!({
                    "information": {"has_data": true, "knowledge_retrieved": true},
                    "targeted_knowledge": targeted,
                }))
            }
            "think_tools" => {
                let outputs = params.get("outputs").cloned().unwrap_or(Value::Null);
                let understand = outputs.get("understand").cloned().unwrap_or(Value::Null);
                let topic = understand.get("topic").and_then(|v| v.as_str()).unwrap_or("").to_lowercase();
                let intent = understand.get("intent").and_then(|v| v.as_str()).unwrap_or("general");

                let tool_output = if ["time", "date", "day", "clock"].iter().any(|kw| topic.contains(kw)) {
                    let now = chrono::Utc::now();
                    format!(
                        "Current date: {}, time: {} UTC, day: {}",
                        now.format("%Y-%m-%d"),
                        now.format("%H:%M:%S"),
                        now.format("%A")
                    )
                } else if ["tool", "capability", "what can"].iter().any(|kw| topic.contains(kw)) {
                    "Available tools: get_time, list_tools. Capabilities: Explain Jeeves architecture; Describe key concepts; Help with getting started".into()
                } else if intent == "general" {
                    "No specific tools needed for this query.".into()
                } else {
                    "No tool results.".into()
                };

                Ok(json!({
                    "information": {"has_data": true, "tools_executed": true},
                    "targeted_knowledge": tool_output,
                }))
            }
            _ => Err(jeeves_core::Error::not_found(format!("Unknown tool: {}", name))),
        }
    }

    fn list_tools(&self) -> Vec<ToolInfo> {
        vec![
            ToolInfo {
                name: "get_time".into(),
                description: "Get current date and time (UTC)".into(),
                parameters: json!({"type": "object", "properties": {}}),
            },
            ToolInfo {
                name: "list_tools".into(),
                description: "List available tools and onboarding capabilities".into(),
                parameters: json!({"type": "object", "properties": {}}),
            },
            ToolInfo {
                name: "think_knowledge".into(),
                description: "Retrieve targeted knowledge sections based on classified intent".into(),
                parameters: json!({"type": "object"}),
            },
            ToolInfo {
                name: "think_tools".into(),
                description: "Invoke tools based on classified topic from understand stage".into(),
                parameters: json!({"type": "object"}),
            },
        ]
    }
}

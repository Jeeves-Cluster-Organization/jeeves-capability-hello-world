# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| < 0.2   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in Jeeves Hello World, please report it responsibly.

### How to Report

1. **Do NOT open a public issue** for security vulnerabilities
2. Email the maintainers directly or use GitHub's private vulnerability reporting feature
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to Expect

- Acknowledgment within 48 hours
- Regular updates on progress
- Credit in the security advisory (if desired)

## Security Considerations

### LLM Provider API Keys

- Never commit API keys to the repository
- Use environment variables for all secrets
- The `.env` file is gitignored by default

```bash
# Correct: Use environment variables
export OPENAI_API_KEY=your_key_here

# Incorrect: Never hardcode
OPENAI_API_KEY = "sk-..."  # DON'T DO THIS
```

### Tool Execution

The chatbot executes tools based on LLM decisions. Current tools are read-only:

| Tool | Risk Level | Notes |
|------|------------|-------|
| `web_search` | External | Makes HTTP requests to search APIs |
| `get_time` | Read-only | No external calls |
| `list_tools` | Read-only | Introspection only |

When adding custom tools:
- Validate all inputs
- Use allowlists, not blocklists
- Implement rate limiting for external calls
- Log tool executions for audit

### Input Validation

User inputs flow through the pipeline:

```
User Input → Understand Agent → Think Agent → Respond Agent → Output
```

- Prompts include instructions to ignore injection attempts
- Tool parameters are validated before execution
- Outputs are sanitized before display

### Database Security

If using PostgreSQL for conversation history:
- Use parameterized queries (SQLAlchemy handles this)
- Don't store sensitive user data in conversation logs
- Implement proper access controls

### Docker Deployment

- Don't run containers as root
- Use read-only file systems where possible
- Keep base images updated
- Don't expose internal services (llama-server, database) publicly

## Dependencies

### Monitoring for Vulnerabilities

```bash
# Check Python dependencies
pip install safety
safety check

# Check for known vulnerabilities
pip-audit
```

### Submodule Security

This repository includes git submodules:
- `jeeves-core` - Rust micro-kernel
- `jeeves-airframe` - Python infrastructure

Keep submodules updated:

```bash
git submodule update --remote --merge
```

## Best Practices for Contributors

1. **Never log sensitive data** - API keys, tokens, personal information
2. **Validate external input** - User messages, API responses
3. **Use secure defaults** - Fail closed, not open
4. **Keep dependencies updated** - Regular security patches
5. **Review tool implementations** - Especially tools with external access

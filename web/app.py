"""Gradio web interface for Dutchkem Model 4.0."""

import json

from agents.llm_client import PROVIDER_ORDER, PROVIDERS


def create_app(model=None):
    """Build and return a Gradio app bound to the given orchestrator."""
    import gradio as gr

    if model is None:
        from orchestrator_v4 import DutchkemModel4
        model = DutchkemModel4()

    provider_names = list(PROVIDER_ORDER) + ["ollama"]
    current_provider = model.architect.llm.selected_provider
    current_model = model.architect.llm.model

    def handle(text, history):
        result = model.process_request(text)
        payload = json.dumps(result, indent=2, default=str)
        return payload, history + [(text, payload)]

    def handle_demo(request_type, prompt):
        command = f"/{request_type} {prompt}"
        result = model.process_request(command)
        return json.dumps(result, indent=2, default=str)

    def handle_model(provider, model_name):
        status = model.set_llm(provider, model_name)
        return json.dumps(status, indent=2, default=str)

    def model_list_for(provider):
        return PROVIDERS.get(provider, {}).get("models", [])

    with gr.Blocks(title="Dutchkem Model 4.0") as app:
        gr.Markdown(
            "# 🧠 Dutchkem Model 4.0 — The Ultimate AI Build System\n"
            "13 specialized agents, full SDLC, security scanning, performance "
            "analysis, sandboxed execution, persistent memory, and more."
        )
        with gr.Tab("Chat"):
            chatbot = gr.Chatbot(height=480)
            msg = gr.Textbox(label="Request", placeholder="Build a microservices e-commerce platform...")
            with gr.Row():
                submit = gr.Button("Send")
                clear = gr.Button("Clear")
            submit.click(handle, [msg, chatbot], [msg, chatbot])
            msg.submit(handle, [msg, chatbot], [msg, chatbot])
            clear.click(lambda: (None, None), None, [chatbot, msg])

        with gr.Tab("Command Center"):
            with gr.Row():
                req_type = gr.Dropdown(
                    choices=[
                        "architect", "design", "os_kernel", "game", "security",
                        "performance", "sdlc", "fleet", "execute",
                    ],
                    value="architect",
                    label="Agent / subsystem",
                )
                prompt = gr.Textbox(label="Prompt", scale=3)
            run = gr.Button("Run")
            out = gr.Textbox(label="Result", lines=20)
            run.click(handle_demo, [req_type, prompt], out)

        with gr.Tab("Model"):
            gr.Markdown(
                "Switch the LLM backend for **all** agents at runtime. "
                "Providers are auto-detected from their env keys; Ollama runs "
                "fully locally with open models like qwen3-coder."
            )
            with gr.Row():
                provider_dd = gr.Dropdown(
                    choices=provider_names,
                    value=current_provider if current_provider in provider_names else "openai",
                    label="Provider",
                )
                model_tb = gr.Dropdown(
                    choices=model_list_for(current_provider),
                    value=current_model,
                    label="Model (pick or type)",
                    allow_custom_value=True,
                    filterable=True,
                )
            provider_dd.change(
                lambda p: gr.update(choices=model_list_for(p)),
                provider_dd,
                model_tb,
            )
            apply_model = gr.Button("Apply Model")
            model_status = gr.JSON(label="Provider status")
            apply_model.click(handle_model, [provider_dd, model_tb], model_status)

    return app

"""QLoRA fine-tune a small instruct model on the ReportLens explainer dataset.

Uses Unsloth for memory-efficient 4-bit LoRA that fits a free Colab T4. Trains on the
chat-format JSONL from build_dataset.py, then optionally exports GGUF so the result can be
served by Ollama (self-hosted, no external API) — keeping ReportLens's core promise.

Run (in Colab, GPU runtime):
    python -m llm_service.finetune.train_lora \
        --data llm_service/artifacts/explainer_sft.jsonl \
        --base unsloth/Qwen2.5-3B-Instruct-bnb-4bit \
        --out llm_service/artifacts/explainer-lora --export-gguf

Deps come from the `finetune` extra (installed in Colab):
    pip install -e "services/llm_service[finetune]"
"""

import argparse


def main() -> None:
    ap = argparse.ArgumentParser(description="QLoRA fine-tune the ReportLens explainer.")
    ap.add_argument("--data", type=str, default="llm_service/artifacts/explainer_sft.jsonl")
    ap.add_argument("--base", type=str, default="unsloth/Qwen2.5-3B-Instruct-bnb-4bit")
    ap.add_argument("--out", type=str, default="llm_service/artifacts/explainer-lora")
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--batch-size", type=int, default=2)
    ap.add_argument("--grad-accum", type=int, default=4)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--max-seq-len", type=int, default=2048)
    ap.add_argument("--lora-rank", type=int, default=16)
    ap.add_argument("--chat-template", type=str, default="qwen-2.5")
    ap.add_argument("--export-gguf", action="store_true", help="also save a q4_k_m GGUF")
    args = ap.parse_args()

    from datasets import load_dataset
    from transformers import TrainingArguments
    from trl import SFTTrainer
    from unsloth import FastLanguageModel, is_bfloat16_supported
    from unsloth.chat_templates import get_chat_template

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.base,
        max_seq_length=args.max_seq_len,
        load_in_4bit=True,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=args.lora_rank,
        lora_alpha=args.lora_rank,
        lora_dropout=0.0,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        use_gradient_checkpointing="unsloth",
        random_state=0,
    )
    tokenizer = get_chat_template(tokenizer, chat_template=args.chat_template)

    dataset = load_dataset("json", data_files=args.data, split="train")

    def _format(example):
        return {
            "text": tokenizer.apply_chat_template(
                example["messages"], tokenize=False, add_generation_prompt=False
            )
        }

    dataset = dataset.map(_format)

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=args.max_seq_len,
        args=TrainingArguments(
            per_device_train_batch_size=args.batch_size,
            gradient_accumulation_steps=args.grad_accum,
            num_train_epochs=args.epochs,
            learning_rate=args.lr,
            fp16=not is_bfloat16_supported(),
            bf16=is_bfloat16_supported(),
            logging_steps=10,
            warmup_steps=10,
            optim="adamw_8bit",
            weight_decay=0.01,
            lr_scheduler_type="linear",
            seed=0,
            output_dir=args.out,
            report_to=[],
        ),
    )

    print("[train] starting QLoRA fine-tuning ...")
    trainer.train()

    model.save_pretrained(args.out)
    tokenizer.save_pretrained(args.out)
    print(f"[done] saved LoRA adapter + tokenizer to {args.out}")

    if args.export_gguf:
        gguf_dir = f"{args.out}-gguf"
        print(f"[gguf] exporting merged q4_k_m GGUF to {gguf_dir} (for Ollama) ...")
        model.save_pretrained_gguf(gguf_dir, tokenizer, quantization_method="q4_k_m")
        print(
            "[gguf] done. Serve with Ollama:\n"
            f"    ollama create reportlens-explainer -f {gguf_dir}/Modelfile\n"
            "  then set OLLAMA_MODEL=reportlens-explainer in the API .env."
        )


if __name__ == "__main__":
    main()

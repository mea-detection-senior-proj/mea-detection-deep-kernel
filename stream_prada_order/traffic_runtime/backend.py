"""Lazy Transformers bridge. Only the authorized, contained worker calls load()."""
from pathlib import Path

from ..traffic_collection.schema import ExecutionDisabled, require, digest
from .policy import profile, limits, Grant


class QwenBackend:
    def __init__(self):
        self.model=self.tokenizer=self.torch=None
        self.pending=None

    def load(self,snapshot,*,execution_authorized=False,grant=None,manifest=None,plan=None):
        if execution_authorized is not True:raise ExecutionDisabled('backend_execution_not_authorized')
        if not isinstance(grant,Grant) or grant.record.get('traffic_kind')!='real':
            raise ExecutionDisabled('validated_real_grant_required')
        grant.check(manifest,plan)
        return self._load_native(snapshot)

    def _load_native(self,snapshot):
        # No imports above this gate instantiate a tokenizer, a model, or a CUDA context.
        import torch
        from transformers import AutoTokenizer, Qwen2ForCausalLM, GenerationConfig
        self.torch=torch;self.GenerationConfig=GenerationConfig
        p=profile();l=limits()
        require(torch.cuda.is_available() and torch.cuda.is_bf16_supported(),'cuda_bf16_unavailable')
        total=torch.cuda.get_device_properties(0).total_memory
        torch.cuda.set_per_process_memory_fraction(l['max_gpu_reserved_bytes']/total,0)
        torch.cuda.reset_peak_memory_stats(0)
        # Authorized future pilot includes a tiny kernel/BF16 probe BEFORE weight loading.
        with torch.inference_mode():
            probe=torch.ones((2,2),device=p['device'],dtype=torch.bfloat16)
            require(bool(torch.isfinite(probe@probe).all().item()),'bf16_kernel_probe_failed')
        del probe
        self.tokenizer=AutoTokenizer.from_pretrained(str(snapshot),local_files_only=True,
                                                     trust_remote_code=False,use_fast=True)
        require(self.tokenizer.chat_template==p['chat_template'],'chat_template_mismatch')
        self.model=Qwen2ForCausalLM.from_pretrained(str(snapshot),local_files_only=True,trust_remote_code=False,
                    use_safetensors=True,dtype=torch.bfloat16,attn_implementation=p['attention'])
        self.model.to(p['device']);self.model.eval()
        self._gpu_guard()

    def _gpu_guard(self):
        require(self.torch.cuda.max_memory_reserved(0)<=limits()['max_gpu_reserved_bytes'],'gpu_reserved_cap_exceeded')

    def prepare(self,query):
        require(self.model is not None and self.pending is None,'backend_not_ready')
        p=profile()
        messages=[{'role':'system','content':p['system_message']},{'role':'user','content':query}]
        rendered=self.tokenizer.apply_chat_template(messages,chat_template=p['chat_template'],tokenize=False,
                                                    add_generation_prompt=True)
        encoded=self.tokenizer(rendered,add_special_tokens=False,padding=False,truncation=False,return_tensors='pt')
        ids=encoded['input_ids'][0].tolist();mask=encoded['attention_mask'][0].tolist()
        require(all(type(i) is int and i>=0 for i in ids) and bool(ids),'invalid_input_ids')
        require(mask==[1]*len(ids),'unexpected_padding')
        require(len(ids)<=limits()['max_input_tokens'],'input_token_cap_exceeded')
        self.pending=(encoded,ids)
        return {'rendered_prompt':rendered,'rendered_prompt_sha256':digest(rendered),
                'input_ids':ids,'input_tokens':len(ids),'chat_template_sha256':p['chat_template_sha256']}

    def generate(self):
        require(self.pending is not None,'prepared_input_required')
        encoded,input_ids=self.pending;self.pending=None;p=profile()
        encoded={name:value.to(p['device']) for name,value in encoded.items()}
        self._gpu_guard()
        with self.torch.inference_mode():
            output=self.model.generate(**encoded,generation_config=self.GenerationConfig(**p['generation']),
                                       return_dict_in_generate=True,output_scores=False)
        self.torch.cuda.synchronize(0);self._gpu_guard()
        sequence=output.sequences[0].tolist()
        require(sequence[:len(input_ids)]==input_ids,'generated_prefix_mismatch')
        ids=sequence[len(input_ids):]
        require(1<=len(ids)<=limits()['max_output_tokens'] and all(type(i) is int and i>=0 for i in ids),'invalid_output_ids')
        text=self.tokenizer.decode(ids,**p['decode'])
        require(type(text) is str and len(text.encode('utf-8'))<=limits()['max_response_bytes'],'output_byte_cap_exceeded')
        return {'text':text,'input_tokens':len(input_ids),'output_tokens':len(ids),'output_ids':ids,
                'gpu_peak_reserved_bytes':self.torch.cuda.max_memory_reserved(0)}

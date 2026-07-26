#!/usr/bin/env python3
import json
import yaml

# Load insights
with open('insights.jsonl', 'r') as f:
    insights = [json.loads(line) for line in f if line.strip()]
insight_ids = set(r['id'] for r in insights)

print(f"Total insights: {len(insights)}")
print(f"Insight IDs: {sorted(insight_ids)}")
print()

# Load hypotheses
with open('hypotheses.yaml', 'r') as f:
    hyps = yaml.safe_load(f) or []
    
print(f'Hypotheses: {len(hyps)}')
for h in hyps:
    missing = [r for r in h.get('derived_from', []) if r not in insight_ids]
    if missing:
        print(f"  FAIL {h['id']}: MISSING REFS: {missing}")
    else:
        print(f"  PASS {h['id']}: OK (refs: {h.get('derived_from', [])})")
print()

# Load requirements
with open('candidate-requirements.yaml', 'r') as f:
    reqs = yaml.safe_load(f) or []
    
print(f'Requirements: {len(reqs)}')
for r in reqs:
    missing = [ref for ref in r.get('derived_from', []) if ref not in insight_ids]
    if missing:
        print(f"  FAIL {r['id']}: MISSING REFS: {missing}")
    else:
        print(f"  PASS {r['id']}: OK (refs: {r.get('derived_from', [])})")
print()

# Invariant check: insights >= hyps + reqs
print(f"Invariant check: insights ({len(insights)}) >= hyps ({len(hyps)}) + reqs ({len(reqs)})?")
print(f"  {len(insights)} >= {len(hyps) + len(reqs)} ? {len(insights) >= len(hyps) + len(reqs)}")

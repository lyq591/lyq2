import json, os

total_empty = 0
for i in range(1, 21):
    path = f'data/processed/FJSP-F{i}.json'
    if not os.path.exists(path):
        print(f'F{i}: MISSING')
        continue
    d = json.load(open(path, 'r', encoding='utf-8'))
    empty = 0
    for j in d['jobs']:
        for op in j['operations']:
            if not op['eligible_machines'] or not op['processing_times'] or not op['eligible_fixtures']:
                empty += 1
    total_empty += empty
    scale = d['scale']
    print(f"F{i}: {scale['num_jobs']}j x {scale['num_machines']}m x {scale['num_fixtures']}f, "
          f"ops/job={scale['operations_per_job']}, empty={empty}")

print(f'\nTotal empty operations: {total_empty}')
print(f'Index exists: {os.path.exists("data/processed/index.json")}')

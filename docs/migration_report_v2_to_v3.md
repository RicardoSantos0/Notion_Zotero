# Migration report: canonical v2 → v3

Left (v2) count: 442
Right (v3) count: 442

Unchanged bundles: 0
Changed bundles: 442
Only in left: 0
Only in right: 0

## Top changed bundles (sample)
- 003e69cb-f908-470d-bab2-c26eed3c63d3.canonical.json
- 00f24000-f241-438b-a023-d872bc2b59e6.canonical.json
- 02eedcf7-bc5a-406e-ba94-01f7e39a25cd.canonical.json
- 02fef9f2-c5c2-47ee-a111-eb7788556c5e.canonical.json
- 033342f8-04d7-4a83-b56e-7d8b056b12e2.canonical.json
- 03b10d6a-c955-46b7-b47e-6ed24bc3cb7b.canonical.json
- 048e79cb-5189-4355-a03c-c4abd1a51afd.canonical.json
- 055e2b8c-f9bc-48df-87e8-b524c949bff7.canonical.json
- 058d7cf3-d0d1-4404-9c00-114f12e17802.canonical.json
- 060989c9-da7d-41d8-9ad2-04ebad13c871.canonical.json
- 07693b77-012d-41f4-a33e-7e9b3cfa22f1.canonical.json
- 08272a7a-133a-43fe-ad78-979dbccf128f.canonical.json
- 0bae74ea-9a64-4781-94b4-cb109c297bfb.canonical.json
- 0bc6ac3e-a597-40c0-b914-eeb5d229c7e8.canonical.json
- 0c06813a-4a18-460a-9912-24c843d6f2a9.canonical.json
- 0eb644e8-8ffa-4903-a6f8-f2837c5ac666.canonical.json
- 0f2dffa6-d4be-4460-a188-6a45a8cef54e.canonical.json
- 0fa04787-ce26-44e3-b823-fb9a424144f9.canonical.json
- 10ee2f9a-073b-4706-8f15-c294d689e319.canonical.json
- 12f21e6c-2353-4ad2-83ae-73557725d22d.canonical.json
- 1320c318-6a70-4c96-aca3-31486b3e5139.canonical.json
- 133c4fbd-ae35-4ae7-97fc-4e354d976fa2.canonical.json
- 136f6fd9-63eb-4df5-8f84-bac60bbfc355.canonical.json
- 15232c7b-7d9a-4574-bb5f-9d11b60ac5fb.canonical.json
- 15256f2e-bb54-496a-8a26-1516956f8dde.canonical.json
- 1786f980-4468-439e-9de8-c3e9ccd24c72.canonical.json
- 17c20953-fb22-4346-b8e5-938e56b2be51.canonical.json
- 18473a97-c64c-40ee-9e2d-f28b7ec74c48.canonical.json
- 1877dfeb-4037-4c72-8c5c-a0fc4127e3ce.canonical.json
- 189f2a61-52f2-477e-b2b4-eebe2934fb4c.canonical.json
- 18b4750c-f3ba-8001-846c-eddab66ea586.canonical.json
- 18b4750c-f3ba-8005-9ff0-d7886becd1e4.canonical.json
- 18b4750c-f3ba-8013-9a0f-c751a75b5143.canonical.json
- 18b4750c-f3ba-8013-a14e-cc3d2eaf6f7b.canonical.json
- 18b4750c-f3ba-8042-b170-f80ea9d94cf9.canonical.json
- 18b4750c-f3ba-8049-9100-dfca1f25a43f.canonical.json
- 18b4750c-f3ba-804e-84e1-f723b57d34a6.canonical.json
- 18b4750c-f3ba-805b-9338-f8d147477c97.canonical.json
- 18b4750c-f3ba-807b-8f2d-cd625bdc13f1.canonical.json
- 18b4750c-f3ba-8086-a22f-f7799f428865.canonical.json
- 18b4750c-f3ba-8093-896a-c6d3305df7f8.canonical.json
- 18b4750c-f3ba-80ac-aebf-e138d8c5fc9b.canonical.json
- 18b4750c-f3ba-80b6-a8a8-dc0f6228781d.canonical.json
- 18b4750c-f3ba-80bf-8703-db27a50b8f28.canonical.json
- 18b4750c-f3ba-80ee-be85-c86f9e7d8bbf.canonical.json
- 18c4750c-f3ba-8008-a03a-c2176d5517a8.canonical.json
- 18c4750c-f3ba-8008-a36d-e58a8865f9e3.canonical.json
- 18c4750c-f3ba-8009-9b80-e3ad7e32e394.canonical.json
- 18c4750c-f3ba-800a-bb2d-f1d25e1094a9.canonical.json
- 18c4750c-f3ba-800f-87b5-dbdbf1d32668.canonical.json

## Notes
- All canonical bundles were regenerated using the new importer which:
  - applies rule-driven task parsers (summary/methods/dataset)
  - replaces random IDs with deterministic `uuid5`-based `*_xxxx` IDs
  - adds a stable `provenance` object to extractions and references
  - normalizes `Status`/`Status_1` into canonical workflow states

## Next steps (recommended)
- Review sample changed bundles for semantic correctness
- Expand registry parsers with domain-specific rules
- Produce a migration audit CSV for downstream review (optional)
import sys
import importlib

ROOT = r"C:/Users/ricar/OneDrive - NOVAIMS/PhD/Publications/Literature Review Paper/Notion_Zotero"
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
importlib.invalidate_caches()
print('sys.path prepared')
try:
    import src.cli as cli
    print('imported src.cli')
    import src.analysis._client as _client
    print('imported src.analysis._client, Client:', getattr(_client, 'Client', None))
except Exception as e:
    print('IMPORT ERROR:', type(e).__name__, e)

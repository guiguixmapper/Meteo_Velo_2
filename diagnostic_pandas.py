#!/usr/bin/env python
"""Diagnostic complet des imports pandas"""

import sys
import os

print("=" * 60)
print("🔍 DIAGNOSTIC PANDAS IMPORTS")
print("=" * 60)

# 1. Vérifier la version de Python
print(f"\n✅ Python version: {sys.version}")
print(f"✅ Python path: {sys.executable}")

# 2. Vérifier que pandas est installé
try:
    import pandas as pd
    print(f"✅ pandas {pd.__version__} installed")
except ImportError as e:
    print(f"❌ pandas NOT installed: {e}")
    sys.exit(1)

# 3. Vérifier chaque fichier qui utilise pd
files_to_check = [
    "core/data_processor.py",
    "app.py",
    "core/services/climbing_service.py",
    "ui/components/climbs_view.py",
    "ui/components/detail_view.py",
    "ui/components/profile_climbs_view.py",
    "tests/test_climbing.py",
]

print(f"\n📁 Checking files for 'import pandas':")
for fname in files_to_check:
    if not os.path.exists(fname):
        print(f"   ⚠️  {fname} NOT FOUND")
        continue
    
    with open(fname, "r", encoding="utf-8") as f:
        content = f.read()
        if "import pandas" in content:
            # Find the line number
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                if "import pandas" in line:
                    print(f"   ✅ {fname} (line {i}): {line.strip()}")
        else:
            print(f"   ❌ {fname} MISSING 'import pandas'")

# 4. Test imports from data_processor
print(f"\n🧪 Testing DataProcessor imports:")
sys.path.insert(0, os.getcwd())
try:
    # Try importing just the module first
    import core.data_processor as dp
    print(f"   ✅ core.data_processor module imported")
    
    # Check if pd is available in that module
    if hasattr(dp, 'pd'):
        print(f"   ✅ pd is accessible in data_processor")
    else:
        print(f"   ⚠️  pd not as module attribute (but might be in namespace)")
    
    # Try to access the class
    if hasattr(dp, 'DataProcessor'):
        print(f"   ✅ DataProcessor class found")
    else:
        print(f"   ❌ DataProcessor class NOT found")
        
except Exception as e:
    print(f"   ❌ Error importing: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("✅ DIAGNOSTIC COMPLETE")
print("=" * 60)

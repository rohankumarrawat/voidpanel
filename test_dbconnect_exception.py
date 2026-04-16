import os
import sys
# A quick patch to print the error in dbconnect
cmd = "sed -i 's/except Exception:/except Exception as e:\\n            print(f\"ERROR in dbconnect: {e}\")/g' /Users/rohan/Downloads/voidpanel-main/control/views.py"
os.system(cmd)

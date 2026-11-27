import os

import hopsworks
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("HOPSWORKS_API_KEY")
if not api_key:
    raise SystemExit("HOPSWORKS_API_KEY is missing in .env")

# project=None is fine if you have only one project
project = hopsworks.login(
    api_key_value=api_key,
    project=os.getenv("HOPSWORKS_PROJECT"),
)

fs = project.get_feature_store()

print("Logged in. Project:", project.name)
print("Feature store:", fs.name)
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

models = [
    'models/text-embedding-004', 
    'models/embedding-001', 
    'models/gemini-embedding-001', 
    'models/gemini-embedding-2-preview',
    'models/gemini-embedding-exp-03-07' # some experimental alias
]

working_models = []
for m in models:
    try:
        res = genai.embed_content(model=m, content='test', task_type='retrieval_document')
        working_models.append(m)
        print("WORKED: " + m)
    except Exception as e:
        print("FAILED: " + m + " - " + str(e))

if len(working_models) == 0:
    print("NO WORKING MODELS FOUND")
else:
    print("WORKING MODELS: ", working_models)

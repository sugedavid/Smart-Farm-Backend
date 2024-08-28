import firebase_admin
import uvicorn
import os

from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from firebase_admin import firestore
from openai import OpenAI

from schemas.analysis_schema import AnalysisRequest, AnalysisResponse

# initialize FastAPI
app = FastAPI()

# CORS configuration
origins = [
    "http://localhost",
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# initialize Firebase Admin SDK
firebase_cred = firebase_admin.credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(firebase_cred)

# initialize firestore db
db = firestore.client()

# initialize OpenAI API
openai_client = OpenAI(api_key=os.getenv("SMART_FARM_OPENAI_API_KEY"))
assistant_id = os.getenv("SMART_FARM_OPENAI_API_KEY")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# redirect to docs
@app.get("/", tags=["API documentation"])
async def open_docs():
    return RedirectResponse(url="/docs")

# generate analyis api
@app.post("/analysis", response_model=AnalysisResponse)
async def generate_analysis(analysis_request: AnalysisRequest):
    try:
        thread_id = analysis_request.thread_id
        if not thread_id:
            # create a new thread
            thread = openai_client.beta.threads.create()
            thread_id = thread.id

            # save user data to firestore
            doc_ref = db.collection("users").document(analysis_request.user_id)
            doc_ref.update(
                {
                    "threadId": thread_id
                }
            )

        instructions = analysis_request.instructions

        # create message
        openai_client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=analysis_request.content
        )

        # run assistant
        openai_client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=analysis_request.assistant_id,
            instructions=instructions,
        )
        # assistant response
        messages = openai_client.beta.threads.messages.list(
            thread_id=thread_id
        )
        message_data = [message.model_dump() for message in messages.data]

        return AnalysisResponse(object=messages.object, data=message_data)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# fetch analyis api
@app.get("/analysis", response_model=AnalysisResponse)
async def list_messages(thread_id: str):
    try:
        messages = openai_client.beta.threads.messages.list(
            thread_id=thread_id
        )

        # convert message instances to dictionaries
        message_data = [message.model_dump() for message in messages.data]

        return AnalysisResponse(object=messages.object, data=message_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("functions.main:app", host="0.0.0.0", port=8000, debug=True, reload=True)
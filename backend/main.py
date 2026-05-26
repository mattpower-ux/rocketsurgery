from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="RocketSurgery API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class WalkthroughRequest(BaseModel):
    query: str

@app.get("/")
def root():
    return {"status": "RocketSurgery API is running"}

@app.post("/walkthrough")
def get_walkthrough(request: WalkthroughRequest):
    return {
        "title": "James Hardie Lap Siding Nailing Schedule",
        "disclaimer": "Manufacturer guidance only. Local codes and AHJ requirements may vary.",
        "steps": [
            {
                "id": 1,
                "instruction": "Find the wall studs before fastening the siding.",
                "detail": "Fasteners should penetrate framing or approved structural sheathing.",
                "imageLabel": "Step 1: Locate studs",
                "hotspots": [
                    {
                        "id": "studs",
                        "label": "Stud spacing",
                        "title": "Stud Spacing",
                        "content": "Common framing is 16 inches on center, but verify the wall."
                    }
                ]
            },
            {
                "id": 2,
                "instruction": "Place the siding board in position with the proper overlap.",
                "detail": "Keep laps consistent and follow the product-specific exposure limits.",
                "imageLabel": "Step 2: Set board overlap",
                "hotspots": [
                    {
                        "id": "overlap",
                        "label": "Overlap",
                        "title": "Lap / Exposure",
                        "content": "Confirm overlap and exposure from the current product manual."
                    }
                ]
            },
            {
                "id": 3,
                "instruction": "Fasten near the top edge according to the manufacturer guide.",
                "detail": "Use corrosion-resistant fasteners suitable for fiber-cement siding.",
                "imageLabel": "Step 3: Nail placement",
                "hotspots": [
                    {
                        "id": "nail",
                        "label": "Nail spec",
                        "title": "Fastener Spec",
                        "content": "Use manufacturer-approved corrosion-resistant siding nails. Exact length and type must be verified from the current James Hardie manual."
                    }
                ]
            }
        ]
    }

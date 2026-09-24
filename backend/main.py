from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from models import ClaimCreate
from database import claims_collection

from datetime import datetime
import uuid


app = FastAPI(title="Bruviti Claim Intelligence API")


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# 1. HEALTH CHECK
# ============================================================

@app.get("/")
def root():
    return {
        "message": "Bruviti Claim Intelligence API is running"
    }


# ============================================================
# 2. CREATE CLAIM
# ============================================================

@app.post("/api/claims")
def create_claim(claim: ClaimCreate):

    claim_data = claim.model_dump(mode="json")

    claim_data["claimId"] = (
        "CLM-" + str(uuid.uuid4())[:8].upper()
    )

    claim_data["status"] = "PROCESSING"

    claim_data["validationStatus"] = "PENDING"

    claim_data["createdAt"] = datetime.utcnow().isoformat()

    # Save claim in MongoDB
    claims_collection.insert_one(claim_data)

    # IMPORTANT:
    # MongoDB automatically adds "_id" to claim_data.
    # We do NOT return "_id" to the frontend because
    # MongoDB ObjectId cannot be directly converted to JSON.

    response_claim = {
        "customer": claim_data["customer"],
        "equipmentModel": claim_data["equipmentModel"],
        "serialNumber": claim_data["serialNumber"],
        "description": claim_data["description"],
        "serviceDate": claim_data["serviceDate"],
        "warrantyStatus": claim_data["warrantyStatus"],
        "claimId": claim_data["claimId"],
        "status": claim_data["status"],
        "validationStatus": claim_data["validationStatus"],
        "createdAt": claim_data["createdAt"]
    }

    return {
        "claimId": claim_data["claimId"],
        "status": claim_data["status"],
        "claim": response_claim
    }


# ============================================================
# 3. AI CLAIM ANALYSIS
# ============================================================

@app.post("/api/claims/{claim_id}/analyze")
def analyze_claim(claim_id: str):

    claim = claims_collection.find_one(
        {"claimId": claim_id}
    )

    if not claim:
        return {
            "error": "Claim not found"
        }

    description = claim["description"].lower()

    # --------------------------------------------------------
    # Rule-based mock AI
    # --------------------------------------------------------

    if (
        "power" in description
        or "stopped working" in description
    ):

        analysis = {
            "category": "Hardware Failure",
            "symptom": "Equipment stopped working",
            "suspectedCause": "Power module failure",
            "affectedPart": "Power Module",
            "severity": "HIGH",
            "resolution": "Inspect or replace power module",
            "warrantyRelevance": True,
            "confidence": 92
        }

    elif (
        "network" in description
        or "connection" in description
    ):

        analysis = {
            "category": "Connectivity Issue",
            "symptom": "Intermittent connectivity",
            "suspectedCause": "Network connection issue",
            "affectedPart": "Network Interface",
            "severity": "MEDIUM",
            "resolution": "Check network connection and interface",
            "warrantyRelevance": True,
            "confidence": 86
        }

    else:

        analysis = {
            "category": "Unknown",
            "symptom": claim["description"],
            "suspectedCause": "Requires investigation",
            "affectedPart": "Unknown",
            "severity": "MEDIUM",
            "resolution": "Manual inspection required",
            "warrantyRelevance": False,
            "confidence": 60
        }

    # Save AI analysis
    claims_collection.update_one(
        {"claimId": claim_id},
        {
            "$set": {
                "analysis": analysis,
                "status": "ANALYZED"
            }
        }
    )

    return {
        "claimId": claim_id,
        "analysis": analysis
    }


# ============================================================
# 4. CONFIDENCE + BUSINESS VALIDATION
# ============================================================

@app.post("/api/claims/{claim_id}/validate")
def validate_claim(claim_id: str):

    claim = claims_collection.find_one(
        {"claimId": claim_id}
    )

    if not claim:
        return {
            "error": "Claim not found"
        }

    analysis = claim.get("analysis")

    if not analysis:
        return {
            "error": "Claim must be analyzed first"
        }

    reasons = []

    confidence = analysis["confidence"]

    # Rule 1: Confidence threshold
    if confidence < 80:
        reasons.append(
            "AI confidence is below 80%"
        )

    # Rule 2: Serial number required
    if not claim.get("serialNumber"):
        reasons.append(
            "Serial number is missing"
        )

    # Rule 3: Critical claims require human review
    if analysis["severity"] == "CRITICAL":
        reasons.append(
            "Critical severity requires human review"
        )

    # Rule 4: Warranty conflict
    if (
        analysis["warrantyRelevance"] is True
        and claim.get("warrantyStatus") == "EXPIRED"
    ):
        reasons.append(
            "AI indicates warranty relevance but warranty is expired"
        )

    # Final validation decision
    if reasons:
        validation_status = "HUMAN_REVIEW"
    else:
        validation_status = "ELIGIBLE_FOR_APPROVAL"

    claims_collection.update_one(
        {"claimId": claim_id},
        {
            "$set": {
                "validationStatus": validation_status,
                "validationReasons": reasons,
                "status": validation_status
            }
        }
    )

    return {
        "claimId": claim_id,
        "confidence": confidence,
        "validationStatus": validation_status,
        "reasons": reasons
    }


# ============================================================
# 5. HUMAN REVIEW
# ============================================================

@app.patch("/api/claims/{claim_id}/review")
def review_claim(
    claim_id: str,
    reviewerComment: str = "",
    decision: str = "ACCEPT"
):

    claim = claims_collection.find_one(
        {"claimId": claim_id}
    )

    if not claim:
        return {
            "error": "Claim not found"
        }

    if decision not in [
        "ACCEPT",
        "REJECT",
        "EDIT"
    ]:
        return {
            "error": "Decision must be ACCEPT, REJECT, or EDIT"
        }

    if decision == "REJECT":
        status = "REJECTED"
    else:
        status = "REVIEWED"

    claims_collection.update_one(
        {"claimId": claim_id},
        {
            "$set": {
                "reviewerComment": reviewerComment,
                "reviewDecision": decision,
                "status": status,
                "reviewedAt": datetime.utcnow().isoformat()
            }
        }
    )

    return {
        "claimId": claim_id,
        "decision": decision,
        "status": status,
        "reviewerComment": reviewerComment
    }


# ============================================================
# 6. APPROVE CLAIM
# ============================================================

@app.post("/api/claims/{claim_id}/approve")
def approve_claim(claim_id: str):

    claim = claims_collection.find_one(
        {"claimId": claim_id}
    )

    if not claim:
        return {
            "error": "Claim not found"
        }

    validation_status = claim.get(
        "validationStatus"
    )

    if validation_status not in [
        "ELIGIBLE_FOR_APPROVAL",
        "REVIEWED"
    ]:
        return {
            "error": "Claim is not eligible for approval"
        }

    claims_collection.update_one(
        {"claimId": claim_id},
        {
            "$set": {
                "status": "APPROVED",
                "validationStatus": "APPROVED",
                "approvedAt": datetime.utcnow().isoformat()
            }
        }
    )

    return {
        "claimId": claim_id,
        "status": "APPROVED"
    }


# ============================================================
# 7. ESCALATE CLAIM
# ============================================================

@app.post("/api/claims/{claim_id}/escalate")
def escalate_claim(claim_id: str):

    claim = claims_collection.find_one(
        {"claimId": claim_id}
    )

    if not claim:
        return {
            "error": "Claim not found"
        }

    claims_collection.update_one(
        {"claimId": claim_id},
        {
            "$set": {
                "status": "ESCALATED",
                "validationStatus": "HUMAN_REVIEW",
                "escalatedAt": datetime.utcnow().isoformat()
            }
        }
    )

    return {
        "claimId": claim_id,
        "status": "ESCALATED"
    }


# ============================================================
# 8. GET ALL CLAIMS
# ============================================================

@app.get("/api/claims")
def get_claims():

    claims = list(
        claims_collection.find(
            {},
            {"_id": 0}
        )
    )

    return {
        "count": len(claims),
        "claims": claims
    }


# ============================================================
# 9. GET ONE CLAIM
# ============================================================

@app.get("/api/claims/{claim_id}")
def get_claim(claim_id: str):

    claim = claims_collection.find_one(
        {"claimId": claim_id},
        {"_id": 0}
    )

    if not claim:
        return {
            "error": "Claim not found"
        }

    return claim


# ============================================================
# 10. EXPORT STRUCTURED CLAIM
# ============================================================

@app.get("/api/claims/{claim_id}/export")
def export_claim(claim_id: str):

    claim = claims_collection.find_one(
        {"claimId": claim_id},
        {"_id": 0}
    )

    if not claim:
        return {
            "error": "Claim not found"
        }

    export_data = {

        "claimId": claim.get("claimId"),

        "customer": claim.get("customer"),

        "equipmentModel": claim.get(
            "equipmentModel"
        ),

        "serialNumber": claim.get(
            "serialNumber"
        ),

        "description": claim.get(
            "description"
        ),

        "serviceDate": claim.get(
            "serviceDate"
        ),

        "warrantyStatus": claim.get(
            "warrantyStatus"
        ),

        "analysis": claim.get(
            "analysis"
        ),

        "confidence": (
            claim.get("analysis", {})
            .get("confidence")
        ),

        "validationStatus": claim.get(
            "validationStatus"
        ),

        "reviewerComment": claim.get(
            "reviewerComment"
        ),

        "finalStatus": claim.get(
            "status"
        )
    }

    return JSONResponse(
        content=export_data
    )
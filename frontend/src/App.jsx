import { useState } from "react";
import "./App.css";

const API = "http://127.0.0.1:8000";

function App() {
  const [claim, setClaim] = useState({
    customer: "",
    equipmentModel: "",
    serialNumber: "",
    description: "",
    serviceDate: "",
    warrantyStatus: "ACTIVE",
  });

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setClaim({
      ...claim,
      [e.target.name]: e.target.value,
    });
  };

  const submitClaim = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await fetch(`${API}/api/claims`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(claim),
      });

      const data = await response.json();
      setResult(data);
    } catch {
      setResult({ error: "Could not connect to backend" });
    }

    setLoading(false);
  };

  const analyzeClaim = async () => {
    if (!result?.claimId) return;

    setLoading(true);

    try {
      const response = await fetch(
        `${API}/api/claims/${result.claimId}/analyze`,
        { method: "POST" }
      );

      const data = await response.json();

      setResult((previous) => ({
        ...previous,
        analysis: data.analysis,
      }));
    } catch {
      setResult((previous) => ({
        ...previous,
        error: "Analysis failed",
      }));
    }

    setLoading(false);
  };

  const validateClaim = async () => {
    if (!result?.claimId) return;

    setLoading(true);

    try {
      const response = await fetch(
        `${API}/api/claims/${result.claimId}/validate`,
        { method: "POST" }
      );

      const data = await response.json();

      setResult((previous) => ({
        ...previous,
        validation: data,
      }));
    } catch {
      setResult((previous) => ({
        ...previous,
        error: "Validation failed",
      }));
    }

    setLoading(false);
  };

  const reviewClaim = async (decision) => {
    if (!result?.claimId) return;

    const comment = window.prompt("Reviewer comment:");

    try {
      const response = await fetch(
        `${API}/api/claims/${result.claimId}/review?decision=${decision}&reviewerComment=${encodeURIComponent(
          comment || ""
        )}`,
        { method: "PATCH" }
      );

      const data = await response.json();

      setResult((previous) => ({
        ...previous,
        review: data,
      }));
    } catch {
      setResult((previous) => ({
        ...previous,
        error: "Review failed",
      }));
    }
  };

  const approveClaim = async () => {
    if (!result?.claimId) return;

    const response = await fetch(
      `${API}/api/claims/${result.claimId}/approve`,
      { method: "POST" }
    );

    const data = await response.json();

    setResult((previous) => ({
      ...previous,
      approval: data,
    }));
  };

  const escalateClaim = async () => {
    if (!result?.claimId) return;

    const response = await fetch(
      `${API}/api/claims/${result.claimId}/escalate`,
      { method: "POST" }
    );

    const data = await response.json();

    setResult((previous) => ({
      ...previous,
      escalation: data,
    }));
  };

  const exportClaim = () => {
    if (!result?.claimId) return;

    window.open(
      `${API}/api/claims/${result.claimId}/export`,
      "_blank"
    );
  };

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>Bruviti Claim Intelligence</h1>
          <p>AI-powered service claim validation platform</p>
        </div>

        <span className="badge">AI CLAIM SYSTEM</span>
      </header>

      <main className="container">

        <section className="card">
          <h2>Service Claim Intake</h2>
          <p className="muted">
            Submit a new service or warranty claim.
          </p>

          <form onSubmit={submitClaim}>

            <div className="grid">

              <input
                name="customer"
                placeholder="Customer Name"
                value={claim.customer}
                onChange={handleChange}
                required
              />

              <input
                name="equipmentModel"
                placeholder="Equipment Model"
                value={claim.equipmentModel}
                onChange={handleChange}
                required
              />

              <input
                name="serialNumber"
                placeholder="Serial Number"
                value={claim.serialNumber}
                onChange={handleChange}
                required
              />

              <input
                type="date"
                name="serviceDate"
                value={claim.serviceDate}
                onChange={handleChange}
                required
              />

              <select
                name="warrantyStatus"
                value={claim.warrantyStatus}
                onChange={handleChange}
              >
                <option value="ACTIVE">Active Warranty</option>
                <option value="EXPIRED">Expired Warranty</option>
              </select>

            </div>

            <textarea
              name="description"
              placeholder="Describe the service issue..."
              value={claim.description}
              onChange={handleChange}
              rows="5"
              required
            />

            <button type="submit" disabled={loading}>
              {loading ? "Processing..." : "Submit Claim"}
            </button>

          </form>
        </section>


        {result && !result.error && (

          <section className="card">

            <div className="result-header">

              <div>
                <h2>Claim: {result.claimId}</h2>

                <p className="muted">
                  Status: {result.status || "PROCESSING"}
                </p>
              </div>

              <span className="status">
                {result.validation?.validationStatus ||
                  result.approval?.status ||
                  result.escalation?.status ||
                  "PROCESSING"}
              </span>

            </div>


            <div className="actions">

              <button onClick={analyzeClaim}>
                Analyze with AI
              </button>

              {result.analysis && (
                <button onClick={validateClaim}>
                  Validate Claim
                </button>
              )}

              {result.validation && (
                <>
                  <button onClick={() => reviewClaim("ACCEPT")}>
                    Accept Review
                  </button>

                  <button onClick={() => reviewClaim("REJECT")}>
                    Reject
                  </button>

                  <button onClick={escalateClaim}>
                    Escalate
                  </button>
                </>
              )}

              <button onClick={approveClaim}>
                Approve
              </button>

              <button onClick={exportClaim}>
                Export JSON
              </button>

            </div>


            {result.analysis && (

              <div className="analysis">

                <h3>AI Claim Intelligence</h3>

                <div className="grid">

                  <Info
                    label="Category"
                    value={result.analysis.category}
                  />

                  <Info
                    label="Symptom"
                    value={result.analysis.symptom}
                  />

                  <Info
                    label="Suspected Cause"
                    value={result.analysis.suspectedCause}
                  />

                  <Info
                    label="Affected Part"
                    value={result.analysis.affectedPart}
                  />

                  <Info
                    label="Severity"
                    value={result.analysis.severity}
                  />

                  <Info
                    label="Confidence"
                    value={`${result.analysis.confidence}%`}
                  />

                </div>

                <div className="resolution">
                  <strong>Resolution:</strong>{" "}
                  {result.analysis.resolution}
                </div>

              </div>
            )}


            {result.validation && (

              <div className="validation">

                <h3>Business Validation</h3>

                <strong>
                  {result.validation.validationStatus}
                </strong>

                {result.validation.reasons?.length > 0 && (
                  <ul>
                    {result.validation.reasons.map(
                      (reason, index) => (
                        <li key={index}>{reason}</li>
                      )
                    )}
                  </ul>
                )}

              </div>
            )}


            {result.review && (

              <div className="validation">

                <h3>Human Review</h3>

                <p>
                  Decision:{" "}
                  <strong>{result.review.decision}</strong>
                </p>

                <p>
                  Comment:{" "}
                  {result.review.reviewerComment || "None"}
                </p>

              </div>
            )}

          </section>
        )}

      </main>
    </div>
  );
}


function Info({ label, value }) {

  return (
    <div className="info">
      <span className="label">{label}</span>
      <strong>{value}</strong>
    </div>
  );

}


export default App;

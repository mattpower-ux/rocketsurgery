import { useState } from "react";
import "./App.css";

const API_URL = "https://rocketsurgery-api.onrender.com";

function App() {
  const [query, setQuery] = useState("");
  const [walkthrough, setWalkthrough] = useState(null);
  const [started, setStarted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [activeHotspot, setActiveHotspot] = useState(null);
  const [complete, setComplete] = useState(false);

  const currentStep = walkthrough?.steps?.[stepIndex];

  async function startWalkthrough() {
    setLoading(true);
    setActiveHotspot(null);
    setComplete(false);
    setStepIndex(0);

    try {
      const response = await fetch(`${API_URL}/walkthrough`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          query: query || "James Hardie siding nailing schedule"
        })
      });

      const data = await response.json();

      setWalkthrough(data);
      setStarted(true);
    } catch (error) {
      alert("Could not load walkthrough from API.");
      console.error(error);
    } finally {
      setLoading(false);
    }
  }

  function newJob() {
    window.speechSynthesis.cancel();
    setQuery("");
    setWalkthrough(null);
    setStarted(false);
    setLoading(false);
    setComplete(false);
    setStepIndex(0);
    setActiveHotspot(null);
  }

  function nextStep() {
    setActiveHotspot(null);

    if (stepIndex < walkthrough.steps.length - 1) {
      setStepIndex(stepIndex + 1);
    } else {
      setComplete(true);
    }
  }

  function previousStep() {
    window.speechSynthesis.cancel();
    setActiveHotspot(null);

    if (stepIndex > 0) {
      setStepIndex(stepIndex - 1);
    } else {
      setStarted(false);
      setWalkthrough(null);
      setComplete(false);
    }
  }

  function readAloud() {
    window.speechSynthesis.cancel();

    const text = `${currentStep.instruction}. ${currentStep.detail}`;
    const utterance = new SpeechSynthesisUtterance(text);

    window.speechSynthesis.speak(utterance);
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbarSpacer"></div>
        <div className="logo">RocketSurgery</div>
        <button className="newJobButton" onClick={newJob}>
          NEW JOB
        </button>
      </header>

      {!started ? (
        <main className="homeScreen">
          <div className="homeBadge">FIELD WALKTHROUGHS</div>

          <h1>What do you need help installing?</h1>

          <input
            className="queryBox"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !loading) {
                startWalkthrough();
              }
            }}
            placeholder="Example: James Hardie siding nailing schedule"
          />

          <button
            className="startButton"
            onClick={startWalkthrough}
            disabled={loading}
          >
            {loading ? "BUILDING WALKTHROUGH..." : "START WALKTHROUGH"}
          </button>
        </main>
      ) : complete ? (
        <main className="completionScreen">
          <div className="completionCard">
            <div className="completionIcon">✓</div>
            <h1>Walkthrough complete</h1>
            <p>
              This job sequence is finished. Start a new job when you are ready
              for the next installation question.
            </p>
            <button className="startButton" onClick={newJob}>
              NEW JOB
            </button>
          </div>
        </main>
      ) : (
        currentStep && (
          <main className="walkthroughScreen">
            <div className="walkthroughTitle">{walkthrough.title}</div>

            <div className="progressText">
              Step {stepIndex + 1} of {walkthrough.steps.length}
            </div>

            <section className="imagePanel">
              <div className={`illustrationFrame ${currentStep.imageUrl ? "realIllustration" : `fakeIllustration stepArt${currentStep.id}`}`}>
                {currentStep.imageUrl ? (
                  <img
                    className="stepImage"
                    src={currentStep.imageUrl}
                    alt={currentStep.imageLabel || currentStep.instruction}
                  />
                ) : null}

                <div className="illustrationLabel">{currentStep.imageLabel}</div>

                {currentStep.hotspots.map((hotspot, index) => (
                  <button
                    key={hotspot.id}
                    className={`hotspot hotspot${index + 1}`}
                    onClick={() => setActiveHotspot(hotspot)}
                    aria-label={hotspot.label}
                  >
                    +
                  </button>
                ))}
              </div>
            </section>

            <section className="captionPanel">
              <p className="instruction">{currentStep.instruction}</p>
              <p className="detail">{currentStep.detail}</p>
            </section>

            {activeHotspot && (
              <section className="specCard">
                <button
                  className="closeSpec"
                  onClick={() => setActiveHotspot(null)}
                >
                  ×
                </button>
                <h3>{activeHotspot.title}</h3>
                <p>{activeHotspot.content}</p>
                <small>Source type: manufacturer installation guide</small>
              </section>
            )}

            <footer className="actionBar">
              <button className="secondaryButton" onClick={previousStep}>
                ← Back
              </button>

              <button className="audioButton" onClick={readAloud}>
                🔊 Read
              </button>

              <button className="doneButton" onClick={nextStep}>
                ✓ Done
              </button>
            </footer>

            <p className="disclaimer">{walkthrough.disclaimer}</p>
          </main>
        )
      )}
    </div>
  );
}

export default App;

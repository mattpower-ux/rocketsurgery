import { useState } from "react";
import "./App.css";
import sampleWalkthrough from "./data/sampleWalkthrough";

function App() {
  const [query, setQuery] = useState("");
  const [started, setStarted] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [activeHotspot, setActiveHotspot] = useState(null);
  const [complete, setComplete] = useState(false);

  const currentStep = sampleWalkthrough.steps[stepIndex];

  function startWalkthrough() {
    setStarted(true);
    setComplete(false);
    setStepIndex(0);
    setActiveHotspot(null);
  }

  function newJob() {
    window.speechSynthesis.cancel();
    setQuery("");
    setStarted(false);
    setComplete(false);
    setStepIndex(0);
    setActiveHotspot(null);
  }

  function nextStep() {
    setActiveHotspot(null);

    if (stepIndex < sampleWalkthrough.steps.length - 1) {
      setStepIndex(stepIndex + 1);
    } else {
      setComplete(true);
    }
  }

  function previousStep() {
    setActiveHotspot(null);

    if (stepIndex > 0) {
      setStepIndex(stepIndex - 1);
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
            placeholder="Example: James Hardie siding nailing schedule"
          />

          <button className="startButton" onClick={startWalkthrough}>
            START WALKTHROUGH
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
        <main className="walkthroughScreen">
          <div className="walkthroughTitle">{sampleWalkthrough.title}</div>

          <div className="progressText">
            Step {stepIndex + 1} of {sampleWalkthrough.steps.length}
          </div>

          <section className="imagePanel">
            <div className={`fakeIllustration stepArt${currentStep.id}`}>
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

          <p className="disclaimer">{sampleWalkthrough.disclaimer}</p>
        </main>
      )}
    </div>
  );
}

export default App;

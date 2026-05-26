import { useState } from "react";
import "./App.css";

const API_URL = "https://rocketsurgery-api.onrender.com";

const BRAND_MODEL_OPTIONS = {
  Moen: ["1222 Posi-Temp", "1225 Cartridge", "1200 Cartridge", "M-Core 1213", "Flo Smart Valve"],
  Delta: ["RP19804", "RP46074", "Monitor 14 Series", "MultiChoice Universal", "RP50587"],
  Kohler: ["GP500520", "GP76851", "GP800820", "Rite-Temp", "K-8304"],
  Pfister: ["974-042", "974-074", "974-292", "974-321", "Avante Cartridge"],
  "American Standard": ["M952100", "M961854", "A954440", "Ceramic Disc Cartridge", "Pressure Balance Cartridge"]
};

const KNOWN_BRANDS = Object.keys(BRAND_MODEL_OPTIONS);

function queryLooksSpecific(query) {
  const normalized = query.toLowerCase();

  return KNOWN_BRANDS.some((brand) =>
    normalized.includes(brand.toLowerCase())
  );
}

function buildSpecificQuery(query, brand, model) {
  const baseQuery = query.trim() || "installation walkthrough";

  if (!brand) {
    return baseQuery;
  }

  if (!model) {
    return `${baseQuery} ${brand}`;
  }

  return `${baseQuery} ${brand} ${model}`;
}

function App() {
  const [query, setQuery] = useState("");
  const [walkthrough, setWalkthrough] = useState(null);
  const [started, setStarted] = useState(false);
  const [clarifying, setClarifying] = useState(false);
  const [installMode, setInstallMode] = useState("");
  const [selectedBrand, setSelectedBrand] = useState("");
  const [selectedModel, setSelectedModel] = useState("");
  const [loading, setLoading] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [activeHotspot, setActiveHotspot] = useState(null);
  const [complete, setComplete] = useState(false);

  const currentStep = walkthrough?.steps?.[stepIndex];
  const availableModels = selectedBrand ? BRAND_MODEL_OPTIONS[selectedBrand] || [] : [];

  async function fetchWalkthrough(finalQuery) {
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
          query: finalQuery || "James Hardie siding nailing schedule"
        })
      });

      const data = await response.json();

      setWalkthrough(data);
      setStarted(true);
      setClarifying(false);
    } catch (error) {
      alert("Could not load walkthrough from API.");
      console.error(error);
    } finally {
      setLoading(false);
    }
  }

  function startWalkthrough() {
    const trimmedQuery = query.trim();

    if (queryLooksSpecific(trimmedQuery)) {
      fetchWalkthrough(trimmedQuery);
      return;
    }

    setClarifying(true);
    setStarted(false);
    setComplete(false);
    setActiveHotspot(null);
  }

  function continueGeneric() {
    setInstallMode("generic");
    fetchWalkthrough(query.trim() || "generic installation walkthrough");
  }

  function continueSpecific() {
    const finalQuery = buildSpecificQuery(query, selectedBrand, selectedModel);
    setInstallMode("specific");
    fetchWalkthrough(finalQuery);
  }

  function newJob() {
    window.speechSynthesis.cancel();
    setQuery("");
    setWalkthrough(null);
    setStarted(false);
    setClarifying(false);
    setInstallMode("");
    setSelectedBrand("");
    setSelectedModel("");
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
      setClarifying(true);
    }
  }

  function backToHome() {
    window.speechSynthesis.cancel();
    setClarifying(false);
    setStarted(false);
    setWalkthrough(null);
    setComplete(false);
    setStepIndex(0);
    setActiveHotspot(null);
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

      {!started && !clarifying ? (
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
            placeholder="Example: replace shower cartridge"
          />

          <button
            className="startButton"
            onClick={startWalkthrough}
            disabled={loading}
          >
            {loading ? "BUILDING WALKTHROUGH..." : "START WALKTHROUGH"}
          </button>
        </main>
      ) : clarifying ? (
        <main className="clarifyScreen">
          <div className="homeBadge">CLARIFY INSTALLATION</div>

          <h1>How specific should this walkthrough be?</h1>

          <p className="clarifyPrompt">
            Query: <strong>{query || "Generic installation walkthrough"}</strong>
          </p>

          <section className="choicePanel">
            <label className={`choiceCard ${installMode === "generic" ? "choiceSelected" : ""}`}>
              <input
                type="radio"
                name="installMode"
                checked={installMode === "generic"}
                onChange={() => setInstallMode("generic")}
              />
              <span>
                <strong>GENERIC</strong>
                <small>Use common installation principles and typical field practice.</small>
              </span>
            </label>

            <label className={`choiceCard ${installMode === "specific" ? "choiceSelected" : ""}`}>
              <input
                type="radio"
                name="installMode"
                checked={installMode === "specific"}
                onChange={() => setInstallMode("specific")}
              />
              <span>
                <strong>SPECIFIC BRAND AND MODEL</strong>
                <small>Use product-specific instructions when manufacturer data is available.</small>
              </span>
            </label>
          </section>

          {installMode === "specific" && (
            <section className="brandModelPanel">
              <label>
                Brand
                <select
                  className="selectBox"
                  value={selectedBrand}
                  onChange={(e) => {
                    setSelectedBrand(e.target.value);
                    setSelectedModel("");
                  }}
                >
                  <option value="">Select brand</option>
                  {KNOWN_BRANDS.map((brand) => (
                    <option key={brand} value={brand}>
                      {brand}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                Model
                <select
                  className="selectBox"
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  disabled={!selectedBrand}
                >
                  <option value="">Select model</option>
                  {availableModels.map((model) => (
                    <option key={model} value={model}>
                      {model}
                    </option>
                  ))}
                </select>
              </label>
            </section>
          )}

          <div className="clarifyActions">
            <button className="secondaryButton" onClick={backToHome}>
              ← Back
            </button>

            {installMode === "generic" ? (
              <button
                className="startButton"
                onClick={continueGeneric}
                disabled={loading}
              >
                {loading ? "BUILDING..." : "CONTINUE GENERIC"}
              </button>
            ) : (
              <button
                className="startButton"
                onClick={continueSpecific}
                disabled={loading || !selectedBrand}
              >
                {loading ? "BUILDING..." : "CONTINUE SPECIFIC"}
              </button>
            )}
          </div>
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

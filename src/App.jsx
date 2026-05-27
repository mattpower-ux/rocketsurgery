import { useState } from "react";
import "./App.css";

const API_URL = "https://rocketsurgery-api.onrender.com";

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
  const [screen, setScreen] = useState("home");

  const [query, setQuery] = useState("");
  const [walkthrough, setWalkthrough] = useState(null);
  const [started, setStarted] = useState(false);
  const [clarifying, setClarifying] = useState(false);
  const [installMode, setInstallMode] = useState("");
  const [productOptions, setProductOptions] = useState({
    category: "generic",
    brands: [],
    query_has_known_brand_and_model: false
  });
  const [selectedBrand, setSelectedBrand] = useState("");
  const [selectedModel, setSelectedModel] = useState("");
  const [loading, setLoading] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [activeHotspot, setActiveHotspot] = useState(null);
  const [complete, setComplete] = useState(false);

  const [adminStatus, setAdminStatus] = useState(null);
  const [adminMessage, setAdminMessage] = useState("");
  const [bulkQueries, setBulkQueries] = useState("");
  const [bulkCatalog, setBulkCatalog] = useState("");
  const [catalogBrand, setCatalogBrand] = useState("");
  const [catalogCategory, setCatalogCategory] = useState("");
  const [catalogModels, setCatalogModels] = useState("");
  const [discoverTopModels, setDiscoverTopModels] = useState(true);
  const [adminLoading, setAdminLoading] = useState(false);

  const [canonicalStatus, setCanonicalStatus] = useState(null);
  const [canonicalKey, setCanonicalKey] = useState("");
  const [canonicalStep, setCanonicalStep] = useState(1);
  const [canonicalFile, setCanonicalFile] = useState(null);

  const [overlayData, setOverlayData] = useState(null);

  const currentStep = walkthrough?.steps?.[stepIndex];
  const availableBrands = productOptions?.brands || [];
  const selectedBrandRecord = availableBrands.find(
    (item) => item.brand === selectedBrand
  );
  const availableModels = selectedBrandRecord?.models || [];

  async function fetchProductOptions(finalQuery) {
    const response = await fetch(
      `${API_URL}/product-options?query=${encodeURIComponent(finalQuery)}`
    );

    if (!response.ok) {
      throw new Error("Could not load product options.");
    }

    return response.json();
  }

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

      await fetchOverlay(finalQuery);

      setStarted(true);
      setClarifying(false);
      setScreen("home");
    } catch (error) {
      alert("Could not load walkthrough from API.");
      console.error(error);
    } finally {
      setLoading(false);
    }
  }


  async function fetchOverlay(finalQuery) {
    try {
      const response = await fetch(
        `${API_URL}/walkthrough/overlay`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            query: finalQuery,
            category: productOptions?.category || "",
            brand: selectedBrand,
            model: selectedModel
          })
        }
      );

      const data = await response.json();

      setOverlayData(data);

    } catch (error) {
      console.error(error);
      setOverlayData(null);
    }
  }


  async function startWalkthrough() {
    const trimmedQuery = query.trim() || "generic installation walkthrough";

    setLoading(true);
    setInstallMode("");
    setSelectedBrand("");
    setSelectedModel("");
    setActiveHotspot(null);
    setComplete(false);

    try {
      const options = await fetchProductOptions(trimmedQuery);
      setProductOptions(options);

      if (options.query_has_known_brand_and_model) {
        fetchWalkthrough(trimmedQuery);
        return;
      }

      setClarifying(true);
      setStarted(false);
      setScreen("home");
    } catch (error) {
      console.error(error);

      setProductOptions({
        category: "generic",
        brands: [],
        query_has_known_brand_and_model: false
      });

      setClarifying(true);
      setStarted(false);
      setScreen("home");
    } finally {
      setLoading(false);
    }
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
    setScreen("home");
    setQuery("");
    setWalkthrough(null);
    setStarted(false);
    setClarifying(false);
    setInstallMode("");
    setProductOptions({
      category: "generic",
      brands: [],
      query_has_known_brand_and_model: false
    });
    setSelectedBrand("");
    setSelectedModel("");
    setLoading(false);
    setComplete(false);
    setStepIndex(0);
    setActiveHotspot(null);
  }

  function openAdmin() {
    window.speechSynthesis.cancel();
    setScreen("admin");
    setStarted(false);
    setClarifying(false);
    setComplete(false);
    setActiveHotspot(null);
    loadAdminStatus();
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
      setInstallMode("");
      setClarifying(true);
    }
  }

  function backToHome() {
    window.speechSynthesis.cancel();
    setScreen("home");
    setClarifying(false);
    setStarted(false);
    setWalkthrough(null);
    setComplete(false);
    setInstallMode("");
    setSelectedBrand("");
    setSelectedModel("");
    setStepIndex(0);
    setActiveHotspot(null);
  }

  function readAloud() {
    window.speechSynthesis.cancel();

    const text = `${currentStep.instruction}. ${currentStep.detail}`;
    const utterance = new SpeechSynthesisUtterance(text);

    window.speechSynthesis.speak(utterance);
  }

  async function loadAdminStatus() {
    setAdminLoading(true);

    try {
      const response = await fetch(`${API_URL}/admin/status`);
      const data = await response.json();

      setAdminStatus(data);
      setAdminMessage("Admin status loaded.");
    } catch (error) {
      console.error(error);
      setAdminMessage("Could not load admin status.");
    } finally {
      setAdminLoading(false);
    }
  }

  async function submitBulkQueries() {
    setAdminLoading(true);
    setAdminMessage("");

    try {
      const response = await fetch(`${API_URL}/admin/bulk-queries`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          raw_text: bulkQueries
        })
      });

      const data = await response.json();

      setAdminMessage(
        `Bulk queries saved. Added ${data.added_count || 0}; duplicates ${data.duplicate_count || 0}.`
      );
      setBulkQueries("");
      loadAdminStatus();
    } catch (error) {
      console.error(error);
      setAdminMessage("Could not save bulk queries.");
    } finally {
      setAdminLoading(false);
    }
  }

  async function submitBulkCatalog() {
    setAdminLoading(true);
    setAdminMessage("");

    try {
      const response = await fetch(`${API_URL}/admin/bulk-catalog`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          raw_text: bulkCatalog
        })
      });

      const data = await response.json();

      setAdminMessage(
        `Bulk catalog saved. Added ${data.added_count || 0}; failed ${data.failed_count || 0}.`
      );

      setBulkCatalog("");
      loadAdminStatus();

    } catch (error) {
      console.error(error);
      setAdminMessage("Could not save bulk catalog entries.");

    } finally {
      setAdminLoading(false);
    }
  }


  async function submitCatalogEntry() {
    setAdminLoading(true);
    setAdminMessage("");

    try {
      const response = await fetch(`${API_URL}/admin/catalog-entry`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          brand: catalogBrand,
          category: catalogCategory,
          models_text: catalogModels,
          discover_top_models: discoverTopModels
        })
      });

      const data = await response.json();

      setAdminMessage(
        `Catalog request saved for ${data.request?.brand || catalogBrand} / ${data.request?.category || catalogCategory}.`
      );
      setCatalogBrand("");
      setCatalogCategory("");
      setCatalogModels("");
      setDiscoverTopModels(true);
      loadAdminStatus();
    } catch (error) {
      console.error(error);
      setAdminMessage("Could not save catalog entry.");
    } finally {
      setAdminLoading(false);
    }
  }


  async function processQueuedWalkthroughs() {
    setAdminLoading(true);
    setAdminMessage("");

    try {
      const response = await fetch(
        `${API_URL}/admin/process-bulk-queries?limit=5`,
        {
          method: "POST"
        }
      );

      const data = await response.json();

      setAdminMessage(
        `Processed ${data.processed_count || 0} walkthroughs. Remaining queued: ${data.remaining_queued || 0}.`
      );

      loadAdminStatus();
    } catch (error) {
      console.error(error);
      setAdminMessage("Could not process queued walkthroughs.");
    } finally {
      setAdminLoading(false);
    }
  }


  async function loadCanonicalStatus() {
    setAdminLoading(true);

    try {
      const response = await fetch(
        `${API_URL}/admin/canonical-image-status`
      );

      const data = await response.json();

      setCanonicalStatus(data);
      setAdminMessage("Canonical image status loaded.");
    } catch (error) {
      console.error(error);
      setAdminMessage("Could not load canonical image status.");
    } finally {
      setAdminLoading(false);
    }
  }


  async function uploadCanonicalImage() {
    if (!canonicalFile || !canonicalKey) {
      return;
    }

    setAdminLoading(true);

    try {
      const formData = new FormData();

      formData.append("canonical_key", canonicalKey);
      formData.append("step_number", canonicalStep);
      formData.append("file", canonicalFile);

      const response = await fetch(
        `${API_URL}/admin/upload-canonical-image`,
        {
          method: "POST",
          body: formData
        }
      );

      const data = await response.json();

      setAdminMessage(
        `Uploaded canonical image: ${data.filename}`
      );

      setCanonicalFile(null);

      loadCanonicalStatus();

    } catch (error) {
      console.error(error);
      setAdminMessage("Could not upload canonical image.");
    } finally {
      setAdminLoading(false);
    }
  }


  async function processModelDiscovery() {
    setAdminLoading(true);
    setAdminMessage("");

    try {
      const response = await fetch(
        `${API_URL}/admin/process-model-discovery?limit=5`,
        {
          method: "POST"
        }
      );

      const data = await response.json();

      const discovered = (data.processed || [])
        .map((item) => `${item.brand} / ${item.category}: ${(item.models || []).join(", ")}`)
        .join(" | ");

      setAdminMessage(
        `Model discovery processed ${data.processed_count || 0} requests. Remaining queued: ${data.remaining_queued || 0}. ${discovered}`
      );

      loadAdminStatus();
    } catch (error) {
      console.error(error);
      setAdminMessage("Could not process model discovery.");
    } finally {
      setAdminLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <button className="adminButton" onClick={openAdmin}>
          ADMIN
        </button>
        <div className="logo">RocketSurgery</div>
        <button className="newJobButton" onClick={newJob}>
          NEW JOB
        </button>
      </header>

      {screen === "admin" ? (
        <main className="adminScreen">
          <div className="homeBadge">ADMIN</div>

          <h1>RocketSurgery Builder</h1>

          <section className="adminCard">
            <div className="adminCardHeader">
              <h2>System Status</h2>
              <button
                className="secondaryButton"
                onClick={loadAdminStatus}
                disabled={adminLoading}
              >
                Refresh
              </button>
            </div>

            {adminStatus ? (
              <div className="adminStats">
                <div>
                  <strong>{adminStatus.bulk_query_count}</strong>
                  <span>Total queries</span>
                </div>

                <div>
                  <strong>{adminStatus.bulk_completed_count || 0}</strong>
                  <span>Completed</span>
                </div>

                <div>
                  <strong>{adminStatus.bulk_queued_count || 0}</strong>
                  <span>Queued</span>
                </div>

                <div>
                  <strong>{adminStatus.bulk_failed_count || 0}</strong>
                  <span>Failed</span>
                </div>

                <div>
                  <strong>{adminStatus.catalog_request_count}</strong>
                  <span>Catalog requests</span>
                </div>

                <div>
                  <strong>{adminStatus.catalog_category_count}</strong>
                  <span>Catalog categories</span>
                </div>
              </div>
            ) : (
              <p className="adminHelp">Click refresh to load admin status.</p>
            )}
          </section>

          <section className="adminCard">
            <h2>Bulk Query Seeder</h2>
            <p className="adminHelp">
              Paste one common installation or repair query per line.
            </p>

            <textarea
              className="adminTextArea"
              value={bulkQueries}
              onChange={(e) => setBulkQueries(e.target.value)}
              placeholder={"replace sink disposal\nreplace toilet\ninstall bathroom exhaust fan\nreplace shower cartridge"}
            />

            <button
              className="startButton"
              onClick={submitBulkQueries}
              disabled={adminLoading || !bulkQueries.trim()}
            >
              SAVE BULK QUERIES
            </button>


            <button
              className="doneButton"
              onClick={processQueuedWalkthroughs}
              disabled={adminLoading}
              style={{ marginTop: "12px" }}
            >
              {adminLoading
                ? "PROCESSING..."
                : "PROCESS QUEUED WALKTHROUGHS"}
            </button>
          </section>

          <section className="adminCard">
            <h2>Bulk Brand Ingestion</h2>

            <p className="adminHelp">
              Paste one brand and category per line using:
              Brand | Category
            </p>

            <textarea
              className="adminTextArea"
              value={bulkCatalog}
              onChange={(e) => setBulkCatalog(e.target.value)}
              placeholder={
                "Kohler | Bidets\nDelta | Shower Valves\nMoen | Kitchen Faucets\nRheem | Heat Pumps\nLeviton | Smart Switches"
              }
            />

            <button
              className="startButton"
              onClick={submitBulkCatalog}
              disabled={adminLoading || !bulkCatalog.trim()}
            >
              SAVE BULK BRAND LIST
            </button>

            <button
              className="doneButton"
              onClick={processModelDiscovery}
              disabled={adminLoading}
              style={{ marginTop: "12px" }}
            >
              {adminLoading
                ? "DISCOVERING..."
                : "PROCESS MODEL DISCOVERY"}
            </button>
          </section>

          <section className="adminCard">
            <div className="adminCardHeader">
              <h2>Canonical Image Manager</h2>

              <button
                className="secondaryButton"
                onClick={loadCanonicalStatus}
                disabled={adminLoading}
              >
                Refresh Images
              </button>
            </div>

            <p className="adminHelp">
              Upload reusable canonical walkthrough images.
            </p>

            <input
              className="queryBox"
              type="text"
              value={canonicalKey}
              onChange={(e) => setCanonicalKey(e.target.value)}
              placeholder="Canonical key, example: replace kitchen faucet"
            />

            <input
              className="queryBox"
              type="number"
              min="1"
              value={canonicalStep}
              onChange={(e) => setCanonicalStep(e.target.value)}
              placeholder="Step number"
            />

            <input
              type="file"
              onChange={(e) => setCanonicalFile(e.target.files?.[0] || null)}
            />

            <button
              className="startButton"
              onClick={uploadCanonicalImage}
              disabled={adminLoading || !canonicalFile || !canonicalKey}
            >
              UPLOAD CANONICAL IMAGE
            </button>

            {canonicalStatus?.sets?.length > 0 && (
              <div className="canonicalGrid">
                {canonicalStatus.sets.map((set) => (
                  <div className="canonicalCard" key={set.slug}>
                    <h3>{set.canonical_key}</h3>

                    <p>
                      {set.available_count} / {set.expected_count} images
                    </p>

                    <div className="canonicalThumbs">
                      {set.images.map((img) => (
                        <div
                          key={img.filename}
                          className={`canonicalThumb ${
                            img.exists ? "exists" : "missing"
                          }`}
                        >
                          {img.exists ? (
                            <img src={img.url} alt={img.filename} />
                          ) : (
                            <div className="missingThumb">
                              Missing
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="adminCard">
            <h2>Brand + Category Catalog Builder</h2>
            <p className="adminHelp">
              Add product categories and known models. Leave models blank to queue top-10 model discovery.
            </p>

            <input
              className="queryBox"
              type="text"
              value={catalogBrand}
              onChange={(e) => setCatalogBrand(e.target.value)}
              placeholder="Brand, example: Kohler"
            />

            <input
              className="queryBox"
              type="text"
              value={catalogCategory}
              onChange={(e) => setCatalogCategory(e.target.value)}
              placeholder="Category, example: Bidets"
            />

            <textarea
              className="adminTextArea small"
              value={catalogModels}
              onChange={(e) => setCatalogModels(e.target.value)}
              placeholder={"Optional models, one per line\nK-8298\nK-4108\nK-5724"}
            />

            <label className="adminCheck">
              <input
                type="checkbox"
                checked={discoverTopModels}
                onChange={(e) => setDiscoverTopModels(e.target.checked)}
              />
              Auto-discover top 10 models later if no models are supplied
            </label>

            <button
              className="startButton"
              onClick={submitCatalogEntry}
              disabled={adminLoading || !catalogBrand.trim() || !catalogCategory.trim()}
            >
              SAVE CATALOG ENTRY
            </button>
          </section>

          {adminMessage && (
            <p className="adminMessage">{adminMessage}</p>
          )}

          <button className="secondaryButton" onClick={backToHome}>
            ← Back to App
          </button>
        </main>
      ) : !started && !clarifying ? (
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
                e.preventDefault();
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
            {loading ? "CHECKING PRODUCT OPTIONS..." : "START WALKTHROUGH"}
          </button>
        </main>
      ) : clarifying ? (
        <main className="clarifyScreen">
          <div className="homeBadge">CLARIFY INSTALLATION</div>

          <h1>Generic or product-specific?</h1>

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
                <small>
                  {availableBrands.length > 0
                    ? "Use product-specific instructions when manufacturer data is available."
                    : "No matching product catalog is loaded yet for this query."}
                </small>
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
                  disabled={availableBrands.length === 0}
                >
                  <option value="">Select brand</option>
                  {availableBrands.map((entry) => (
                    <option key={entry.brand} value={entry.brand}>
                      {entry.brand}
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

            {installMode === "specific" ? (
              <button
                className="startButton"
                onClick={continueSpecific}
                disabled={loading || !selectedBrand}
              >
                {loading ? "BUILDING..." : "CONTINUE SPECIFIC"}
              </button>
            ) : installMode === "generic" ? (
              <button
                className="startButton"
                onClick={continueGeneric}
                disabled={loading}
              >
                {loading ? "BUILDING..." : "CONTINUE GENERIC"}
              </button>
            ) : (
              <button className="startButton" disabled>
                CHOOSE AN OPTION
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

            {walkthrough.estimated_labor_label && (
              <section className="laborEstimateCard">
                <div className="laborEstimateIcon">🛠</div>
                <div>
                  <strong>{walkthrough.estimated_labor_label}</strong>
                  <span>Generic estimate before model-specific adjustments.</span>
                </div>
              </section>
            )}

            {installMode === "specific" &&
              overlayData?.overlays?.length > 0 && (
              <section className="overlayPanel">
                <h3>MODEL-SPECIFIC NOTES</h3>

                <div className="overlayGrid">
                  {overlayData.overlays.map((overlay, index) => (
                    <div
                      key={`${overlay.title}-${index}`}
                      className={`overlayCard overlay-${overlay.type}`}
                    >
                      <strong>{overlay.title}</strong>
                      <p>{overlay.content}</p>

                      <small>
                        {overlay.type.replace("_", " ").toUpperCase()}
                      </small>
                    </div>
                  ))}
                </div>
              </section>
            )}

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

                {installMode === "specific" &&
                  currentStep.hotspots.map((hotspot, index) => (
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
                {stepIndex < walkthrough.steps.length - 1
                  ? "NEXT →"
                  : "✓ DONE"}
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

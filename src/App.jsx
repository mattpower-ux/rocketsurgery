import { useEffect, useState } from "react";
import "./App.css";

const API_URL = "https://rocketsurgery-api.onrender.com";

function displayText(value, max = 140) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (text.length <= max) return text;
  return `${text.slice(0, max).trim()}…`;
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

  const [imageRegistry, setImageRegistry] = useState(null);
  const [promoteFilename, setPromoteFilename] = useState("");
  const [promoteCanonicalKey, setPromoteCanonicalKey] = useState("");
  const [promoteStepNumber, setPromoteStepNumber] = useState(1);

  const [buildStatus, setBuildStatus] = useState(null);

  const [bulkJobList, setBulkJobList] = useState(null);
  const [walkthroughList, setWalkthroughList] = useState([]);
  const [selectedAdminWalkthrough, setSelectedAdminWalkthrough] = useState(null);
  const [repairCorrections, setRepairCorrections] = useState({});
  const [repairStatus, setRepairStatus] = useState({});

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
    loadBulkJobList();
    loadAdminWalkthroughs();
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


  async function loadImageRegistry() {
    setAdminLoading(true);

    try {
      const response = await fetch(`${API_URL}/admin/image-registry`);
      const data = await response.json();

      setImageRegistry(data);
      setAdminMessage(`Image registry loaded: ${data.image_count || 0} assets.`);
    } catch (error) {
      console.error(error);
      setAdminMessage("Could not load image registry.");
    } finally {
      setAdminLoading(false);
    }
  }


  async function rebuildImageRegistry() {
    setAdminLoading(true);

    try {
      const response = await fetch(
        `${API_URL}/admin/rebuild-image-registry`,
        {
          method: "POST"
        }
      );

      const data = await response.json();

      setImageRegistry(data);
      setAdminMessage(`Image registry rebuilt: ${data.image_count || 0} assets.`);
    } catch (error) {
      console.error(error);
      setAdminMessage("Could not rebuild image registry.");
    } finally {
      setAdminLoading(false);
    }
  }


  async function promoteImageToCanonical(filenameOverride = "") {
    const filename = filenameOverride || promoteFilename;

    if (!filename || !promoteCanonicalKey) {
      setAdminMessage("Choose an image filename and canonical key first.");
      return;
    }

    setAdminLoading(true);

    try {
      const response = await fetch(`${API_URL}/admin/promote-image`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          filename,
          canonical_key: promoteCanonicalKey,
          step_number: Number(promoteStepNumber || 1)
        })
      });

      const data = await response.json();

      setAdminMessage(
        data.status === "promoted"
          ? `Promoted ${filename} to ${data.filename}.`
          : data.message || "Image promotion failed."
      );

      loadCanonicalStatus();
      loadImageRegistry();

    } catch (error) {
      console.error(error);
      setAdminMessage("Could not promote image.");
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


  async function loadBuildStatus() {
    try {
      const response = await fetch(
        `${API_URL}/admin/walkthrough-build-status`
      );

      const data = await response.json();

      setBuildStatus(data);

    } catch (error) {
      console.error(error);
    }
  }


  async function loadBulkJobList() {
    setAdminLoading(true);

    try {
      const response = await fetch(`${API_URL}/admin/bulk-query-list`);
      const data = await response.json();

      setBulkJobList(data);
      setAdminMessage(`Queue loaded: ${data.counts?.queued || 0} queued, ${data.counts?.failed || 0} failed.`);
    } catch (error) {
      console.error(error);
      setAdminMessage("Could not load walkthrough queue.");
    } finally {
      setAdminLoading(false);
    }
  }


  async function updateBulkJob(querySlug, action) {
    setAdminLoading(true);

    const endpointMap = {
      retry: "bulk-query-retry",
      ignore: "bulk-query-ignore",
      delete: "bulk-query-delete"
    };

    try {
      const response = await fetch(`${API_URL}/admin/${endpointMap[action]}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          query_slug: querySlug
        })
      });

      const data = await response.json();
      setAdminMessage(`Queue item ${data.status || action}.`);
      loadBulkJobList();
      loadAdminStatus();
    } catch (error) {
      console.error(error);
      setAdminMessage("Could not update queue item.");
    } finally {
      setAdminLoading(false);
    }
  }


  async function loadAdminWalkthroughs() {
    setAdminLoading(true);

    try {
      const response = await fetch(`${API_URL}/admin/walkthroughs?limit=250`);
      const data = await response.json();

      setWalkthroughList(data.walkthroughs || []);
    } catch (error) {
      console.error(error);
      setAdminMessage("Could not load walkthrough list.");
    } finally {
      setAdminLoading(false);
    }
  }


  async function loadAdminWalkthrough(walkthroughId) {
    setAdminLoading(true);

    try {
      const response = await fetch(`${API_URL}/admin/walkthroughs/${encodeURIComponent(walkthroughId)}`);
      const data = await response.json();

      if (data.walkthrough) {
        setSelectedAdminWalkthrough(data.walkthrough);
        setRepairCorrections({});
        setRepairStatus({});
        setAdminMessage(`Loaded ${data.walkthrough.title || walkthroughId}.`);
      } else {
        setAdminMessage("Walkthrough not found.");
      }
    } catch (error) {
      console.error(error);
      setAdminMessage("Could not load walkthrough.");
    } finally {
      setAdminLoading(false);
    }
  }


  async function regenerateStepImage(stepId) {
    if (!selectedAdminWalkthrough) {
      return;
    }

    const correction = (repairCorrections[stepId] || "").trim();
    setAdminLoading(true);
    setAdminMessage(`Regenerating image for step ${stepId}. This can take a minute...`);
    setRepairStatus((current) => ({
      ...current,
      [stepId]: "Generating new image..."
    }));

    try {
      const response = await fetch(`${API_URL}/admin/regenerate-step-image`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        cache: "no-store",
        body: JSON.stringify({
          walkthrough_id: selectedAdminWalkthrough.walkthrough_id,
          step_id: stepId,
          correction
        })
      });

      let data = {};
      try {
        data = await response.json();
      } catch (parseError) {
        const text = await response.text();
        throw new Error(text || `Server returned ${response.status}`);
      }

      if (!response.ok) {
        throw new Error(data.detail || data.error || data.message || `Server returned ${response.status}`);
      }

      if (data.walkthrough) {
        setSelectedAdminWalkthrough(data.walkthrough);
      }

      if (data.status === "pending_review") {
        setRepairStatus((current) => ({
          ...current,
          [stepId]: "New candidate generated. Compare it with the current image, then keep or discard."
        }));
        setAdminMessage("New image generated for review.");
      } else {
        setRepairStatus((current) => ({
          ...current,
          [stepId]: `Image regeneration returned: ${data.status || "unknown status"}`
        }));
        setAdminMessage(`Image regeneration: ${data.status || "unknown status"}`);
      }
    } catch (error) {
      console.error(error);
      const message = error?.message || "Could not regenerate image.";
      setRepairStatus((current) => ({
        ...current,
        [stepId]: `Error: ${message}`
      }));
      setAdminMessage(`Could not regenerate image: ${message}`);
    } finally {
      setAdminLoading(false);
    }
  }


  async function acceptStepImage(stepId) {
    if (!selectedAdminWalkthrough) {
      return;
    }

    setAdminLoading(true);

    try {
      const response = await fetch(`${API_URL}/admin/accept-step-image`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          walkthrough_id: selectedAdminWalkthrough.walkthrough_id,
          step_id: stepId
        })
      });

      const data = await response.json();

      if (data.walkthrough) {
        setSelectedAdminWalkthrough(data.walkthrough);
      }

      setAdminMessage(`Image ${data.status}.`);
      loadAdminWalkthroughs();
    } catch (error) {
      console.error(error);
      setAdminMessage("Could not accept image.");
    } finally {
      setAdminLoading(false);
    }
  }


  async function revertStepImage(stepId) {
    if (!selectedAdminWalkthrough) {
      return;
    }

    setAdminLoading(true);

    try {
      const response = await fetch(`${API_URL}/admin/revert-step-image`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          walkthrough_id: selectedAdminWalkthrough.walkthrough_id,
          step_id: stepId
        })
      });

      const data = await response.json();

      if (data.walkthrough) {
        setSelectedAdminWalkthrough(data.walkthrough);
      }

      setAdminMessage(`Image ${data.status}.`);
    } catch (error) {
      console.error(error);
      setAdminMessage("Could not revert image.");
    } finally {
      setAdminLoading(false);
    }
  }


  useEffect(() => {
    if (screen !== "admin") {
      return;
    }

    loadBuildStatus();

    const interval = setInterval(() => {
      loadBuildStatus();
    }, 15000);

    return () => clearInterval(interval);

  }, [screen]);


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
            <div className="adminCardHeader">
              <h2>Walkthrough Build Activity</h2>

              <button
                className="secondaryButton"
                onClick={loadBuildStatus}
              >
                Refresh Activity
              </button>
            </div>

            {buildStatus ? (
              <>
                <div className="adminStats">
                  <div>
                    <strong>{buildStatus.activity_state?.toUpperCase()}</strong>
                    <span>Activity</span>
                  </div>

                  <div>
                    <strong>
                      {buildStatus.seconds_since_activity
                        ? Math.round(buildStatus.seconds_since_activity)
                        : 0}
                    </strong>
                    <span>Seconds idle</span>
                  </div>

                  <div>
                    <strong>{buildStatus.walkthrough_count || 0}</strong>
                    <span>Walkthroughs</span>
                  </div>

                  <div>
                    <strong>{buildStatus.image_count || 0}</strong>
                    <span>Images</span>
                  </div>
                </div>

                <div className="activityColumns">
                  <div>
                    <h3>Recent Walkthroughs</h3>

                    <ul className="activityList">
                      {(buildStatus.recent_walkthroughs || []).map((item) => (
                        <li key={item.name}>
                          <strong>{item.name}</strong>
                          <small>{item.modified_at}</small>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div>
                    <h3>Recent Images</h3>

                    <ul className="activityList">
                      {(buildStatus.recent_images || []).map((item) => (
                        <li key={item.name}>
                          <strong>{item.name}</strong>
                          <small>{item.modified_at}</small>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </>
            ) : (
              <p className="adminHelp">
                Loading build activity...
              </p>
            )}
          </section>

          <section className="adminCard">
            <div className="adminCardHeader">
              <h2>Walkthrough Queue Manager</h2>

              <button
                className="secondaryButton"
                onClick={loadBulkJobList}
                disabled={adminLoading}
              >
                Refresh Queue
              </button>
            </div>

            <p className="adminHelp">
              Review failed, queued, and completed walkthrough jobs. Failed items can be retried, ignored, or removed.
            </p>

            {bulkJobList ? (
              <>
                <div className="adminStats">
                  <div>
                    <strong>{bulkJobList.counts?.queued || 0}</strong>
                    <span>Queued</span>
                  </div>

                  <div>
                    <strong>{bulkJobList.counts?.failed || 0}</strong>
                    <span>Failed</span>
                  </div>

                  <div>
                    <strong>{bulkJobList.counts?.completed || 0}</strong>
                    <span>Completed</span>
                  </div>

                  <div>
                    <strong>{bulkJobList.counts?.ignored || 0}</strong>
                    <span>Ignored</span>
                  </div>
                </div>

                <div style={{ display: "grid", gap: "12px", marginTop: "16px" }}>
                  {(["failed", "queued", "completed", "ignored"]).map((groupName) => (
                    <div key={groupName}>
                      <h3 style={{ textTransform: "capitalize" }}>{groupName}</h3>

                      {(bulkJobList[groupName] || []).slice(0, 30).length === 0 ? (
                        <p className="adminHelp">No {groupName} jobs.</p>
                      ) : (
                        <div style={{ display: "grid", gap: "8px" }}>
                          {(bulkJobList[groupName] || []).slice(0, 30).map((job) => (
                            <div
                              key={`${groupName}-${job.query_slug || job.query}`}
                              style={{
                                border: "1px solid rgba(0,0,0,0.12)",
                                borderRadius: "12px",
                                padding: "12px",
                                background: "rgba(255,255,255,0.75)"
                              }}
                            >
                              <strong title={job.query}>{displayText(job.query, 120)}</strong>

                              <div
                                title={job.walkthrough_id || job.query_slug || "not built yet"}
                                style={{
                                  fontSize: "12px",
                                  opacity: 0.8,
                                  marginTop: "4px",
                                  overflowWrap: "anywhere"
                                }}
                              >
                                ID: {displayText(job.walkthrough_id || job.query_slug || "not built yet", 90)} · Attempts: {job.attempts || 0}
                              </div>

                              {job.quarantine_reason && (
                                <div style={{ fontSize: "12px", color: "#8a5a00", marginTop: "6px", overflowWrap: "anywhere" }}>
                                  Quarantined: {displayText(job.quarantine_reason, 180)}
                                </div>
                              )}

                              {job.error && (
                                <div title={job.error} style={{ fontSize: "12px", color: "#8a1f11", marginTop: "6px", overflowWrap: "anywhere" }}>
                                  Error: {displayText(job.error, 220)}
                                </div>
                              )}

                              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginTop: "10px" }}>
                                <button
                                  className="secondaryButton"
                                  onClick={() => updateBulkJob(job.query_slug, "retry")}
                                  disabled={adminLoading}
                                >
                                  Retry
                                </button>

                                <button
                                  className="secondaryButton"
                                  onClick={() => updateBulkJob(job.query_slug, "ignore")}
                                  disabled={adminLoading}
                                >
                                  Ignore
                                </button>

                                <button
                                  className="secondaryButton"
                                  onClick={() => updateBulkJob(job.query_slug, "delete")}
                                  disabled={adminLoading}
                                >
                                  Delete
                                </button>

                                {job.walkthrough_id && (
                                  <button
                                    className="secondaryButton"
                                    onClick={() => loadAdminWalkthrough(job.walkthrough_id)}
                                    disabled={adminLoading}
                                  >
                                    Inspect
                                  </button>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <p className="adminHelp">Click Refresh Queue to load bulk job records.</p>
            )}
          </section>

          <section className="adminCard">
            <div className="adminCardHeader">
              <h2>Walkthrough Repair Studio</h2>

              <button
                className="secondaryButton"
                onClick={loadAdminWalkthroughs}
                disabled={adminLoading}
              >
                Refresh Walkthroughs
              </button>
            </div>

            <p className="adminHelp">
              Open a saved walkthrough, cherry-pick a weak step image, describe the correction, regenerate it, then accept or discard the replacement.
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "minmax(220px, 320px) 1fr", gap: "16px" }}>
              <div style={{ display: "grid", gap: "8px", alignContent: "start", maxHeight: "680px", overflow: "auto" }}>
                {(walkthroughList || []).slice(0, 100).map((item) => (
                  <button
                    key={item.walkthrough_id}
                    className="secondaryButton"
                    style={{ textAlign: "left" }}
                    onClick={() => loadAdminWalkthrough(item.walkthrough_id)}
                    disabled={adminLoading}
                  >
                    <strong>{item.title}</strong>
                    <br />
                    <span style={{ fontSize: "12px", opacity: 0.75 }}>
                      {item.walkthrough_id} · {item.step_count} steps
                    </span>
                  </button>
                ))}
              </div>

              <div>
                {selectedAdminWalkthrough ? (
                  <>
                    <h3>{selectedAdminWalkthrough.title}</h3>
                    <p className="adminHelp">{selectedAdminWalkthrough.walkthrough_id}</p>

                    <div style={{ display: "grid", gap: "16px" }}>
                      {(selectedAdminWalkthrough.steps || []).map((step) => (
                        <div
                          key={step.id}
                          style={{
                            border: "1px solid rgba(0,0,0,0.14)",
                            borderRadius: "16px",
                            padding: "14px",
                            background: "rgba(255,255,255,0.8)"
                          }}
                        >
                          <h4>{step.imageLabel || `Step ${step.id}`}</h4>
                          <p>{step.instruction}</p>
                          <p style={{ fontSize: "13px", opacity: 0.8 }}>{step.detail}</p>

                          <div style={{ display: "grid", gridTemplateColumns: step.pendingImageUrl ? "1fr 1fr" : "1fr", gap: "12px" }}>
                            <div>
                              <div style={{ fontSize: "12px", fontWeight: 700, marginBottom: "6px" }}>Current Image</div>
                              {step.imageUrl ? (
                                <img
                                  src={step.imageUrl.startsWith("http") ? step.imageUrl : `${API_URL}${step.imageUrl}`}
                                  alt={step.imageLabel || `Step ${step.id}`}
                                  style={{ width: "100%", borderRadius: "12px", border: "1px solid rgba(0,0,0,0.1)" }}
                                />
                              ) : (
                                <div className="missingThumb">No image</div>
                              )}
                            </div>

                            {step.pendingImageUrl && (
                              <div>
                                <div style={{ fontSize: "12px", fontWeight: 700, marginBottom: "6px" }}>New Candidate</div>
                                <img
                                  src={step.pendingImageUrl.startsWith("http") ? step.pendingImageUrl : `${API_URL}${step.pendingImageUrl}`}
                                  alt={`New candidate for step ${step.id}`}
                                  style={{ width: "100%", borderRadius: "12px", border: "2px solid rgba(0,120,255,0.35)" }}
                                />
                              </div>
                            )}
                          </div>

                          <textarea
                            className="adminTextArea small"
                            style={{ marginTop: "12px" }}
                            value={repairCorrections[step.id] || ""}
                            onChange={(e) => setRepairCorrections({
                              ...repairCorrections,
                              [step.id]: e.target.value
                            })}
                            placeholder="Correction prompt, example: Make the pipe copper, remove PVC, show a propane torch heating the joint."
                          />

                          {repairStatus[step.id] && (
                            <p style={{ fontSize: "13px", fontWeight: 700, marginTop: "8px" }}>
                              {repairStatus[step.id]}
                            </p>
                          )}

                          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                            <button
                              type="button"
                              className="startButton"
                              onClick={() => regenerateStepImage(step.id)}
                              disabled={adminLoading}
                            >
                              Regenerate This Image
                            </button>

                            {step.pendingImageUrl && (
                              <button
                                type="button"
                                className="doneButton"
                                onClick={() => acceptStepImage(step.id)}
                                disabled={adminLoading}
                              >
                                Keep New Image
                              </button>
                            )}

                            <button
                              className="secondaryButton"
                              onClick={() => revertStepImage(step.id)}
                              disabled={adminLoading}
                            >
                              Revert / Discard
                            </button>

                            <button
                              className="secondaryButton"
                              onClick={() => {
                                const filename = (step.imageUrl || "").split("/").pop();
                                setPromoteFilename(filename);
                                setPromoteStepNumber(step.id);
                              }}
                              disabled={!step.imageUrl}
                            >
                              Stage for Canonical Promotion
                            </button>
                          </div>

                          {step.imagePrompt && (
                            <details style={{ marginTop: "10px", fontSize: "12px" }}>
                              <summary>Prompt history</summary>
                              <pre style={{ whiteSpace: "pre-wrap" }}>{step.imagePrompt}</pre>
                            </details>
                          )}
                        </div>
                      ))}
                    </div>
                  </>
                ) : (
                  <p className="adminHelp">Select a walkthrough to inspect and repair its images.</p>
                )}
              </div>
            </div>
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


            <div
              style={{
                display: "flex",
                gap: "12px",
                flexWrap: "wrap",
                marginTop: "12px"
              }}
            >
              <button
                className="doneButton"
                onClick={processQueuedWalkthroughs}
                disabled={adminLoading}
              >
                {adminLoading
                  ? "PROCESSING..."
                  : "RUN 5 JOBS"}
              </button>

              <button
                className="secondaryButton"
                onClick={async () => {
                  setAdminLoading(true);

                  try {
                    const response = await fetch(
                      `${API_URL}/admin/process-bulk-queries?limit=1`,
                      {
                        method: "POST"
                      }
                    );

                    const data = await response.json();

                    setAdminMessage(
                      `Worker Automation processed ${data.processed_count || 0} job. Remaining queued: ${data.remaining_queued || 0}.`
                    );

                    loadAdminStatus();
                    loadBuildStatus();

                  } catch (error) {
                    console.error(error);
                    setAdminMessage("Worker Automation failed.");

                  } finally {
                    setAdminLoading(false);
                  }
                }}
                disabled={adminLoading}
              >
                WORKER AUTOMATION
              </button>

              <button
                className="secondaryButton"
                onClick={async () => {
                  setAdminLoading(true);

                  try {
                    const response = await fetch(
                      `${API_URL}/admin/process-bulk-queries?limit=20`,
                      {
                        method: "POST"
                      }
                    );

                    const data = await response.json();

                    setAdminMessage(
                      `Processed ${data.processed_count || 0} walkthroughs. Remaining queued: ${data.remaining_queued || 0}.`
                    );

                    loadAdminStatus();
                    loadBuildStatus();

                  } catch (error) {
                    console.error(error);
                    setAdminMessage("Could not process walkthroughs.");

                  } finally {
                    setAdminLoading(false);
                  }
                }}
                disabled={adminLoading}
              >
                RUN 20 JOBS
              </button>
            </div>
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
            <div className="adminCardHeader">
              <h2>Generated Image Registry</h2>

              <div>
                <button
                  className="secondaryButton"
                  onClick={loadImageRegistry}
                  disabled={adminLoading}
                >
                  Load Registry
                </button>

                <button
                  className="secondaryButton"
                  onClick={rebuildImageRegistry}
                  disabled={adminLoading}
                  style={{ marginLeft: "8px" }}
                >
                  Rebuild
                </button>
              </div>
            </div>

            <p className="adminHelp">
              Review generated images and promote useful ones into canonical image sets.
            </p>

            <input
              className="queryBox"
              type="text"
              value={promoteCanonicalKey}
              onChange={(e) => setPromoteCanonicalKey(e.target.value)}
              placeholder="Promote to canonical key, example: replace toilet"
            />

            <input
              className="queryBox"
              type="number"
              min="1"
              value={promoteStepNumber}
              onChange={(e) => setPromoteStepNumber(e.target.value)}
              placeholder="Canonical step number"
            />

            <input
              className="queryBox"
              type="text"
              value={promoteFilename}
              onChange={(e) => setPromoteFilename(e.target.value)}
              placeholder="Optional filename to promote manually"
            />

            <button
              className="startButton"
              onClick={() => promoteImageToCanonical()}
              disabled={adminLoading || !promoteFilename || !promoteCanonicalKey}
            >
              PROMOTE MANUAL FILENAME
            </button>

            {imageRegistry?.images?.length > 0 && (
              <div className="canonicalGrid">
                {imageRegistry.images.slice(0, 60).map((image) => (
                  <div className="canonicalCard" key={image.filename}>
                    <h3>{image.filename}</h3>

                    <p>
                      {Math.round((image.size_bytes || 0) / 1024)} KB
                    </p>

                    <div className="canonicalThumbs">
                      <div className="canonicalThumb exists">
                        <img
                          src={`${API_URL}/static/images/${image.filename}`}
                          alt={image.filename}
                        />
                      </div>
                    </div>

                    <button
                      className="secondaryButton"
                      onClick={() => {
                        setPromoteFilename(image.filename);
                        promoteImageToCanonical(image.filename);
                      }}
                      disabled={adminLoading || !promoteCanonicalKey}
                    >
                      Promote
                    </button>
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

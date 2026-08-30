import { useEffect, useRef, useState } from "react";
import "./App.css";

const API_URL = (import.meta.env.VITE_API_URL || "https://rocketsurgery-api.onrender.com").replace(/\/$/, "");
const ADMIN_TOKEN_STORAGE_KEY = "rocketsurgery_admin_token";
const qcDraftValueCache = new Map();
const IMAGE_DIRECTION_PLACEHOLDER = "Image direction: clarify what the new image should show, avoid, or emphasize.";

function cacheBustUrl(url) {
  const value = String(url || "").trim();
  if (!value) return "";
  const separator = value.includes("?") ? "&" : "?";
  return `${value}${separator}v=${Date.now()}`;
}

function qcImageDirectionCacheKey(walkthroughId, stepIndex) {
  return `${walkthroughId}-${stepIndex}-imageDirection`;
}

function displayText(value, max = 140) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (text.length <= max) return text;
  return `${text.slice(0, max).trim()}…`;
}


function apiAssetUrl(url) {
  const value = String(url || "").trim();
  if (!value) return "";
  if (value.startsWith("http://") || value.startsWith("https://")) return value;
  if (value.startsWith("/")) return `${API_URL}${value}`;
  return value;
}

function todayDateInputValue() {
  return new Date().toISOString().slice(0, 10);
}

function formatVisitorDate(value) {
  if (!value) return "Unknown";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function formatDuration(seconds) {
  const value = Number(seconds || 0);
  if (!Number.isFinite(value) || value <= 0) return "0s";
  if (value < 60) return `${Math.round(value)}s`;
  return `${Math.floor(value / 60)}m ${Math.round(value % 60)}s`;
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


function StepRepairPromptBox({ stepId, initialValue = "", onDraftChange, onCommit }) {
  const [value, setValue] = useState(initialValue || "");
  const lastStepRef = useRef(stepId);
  const maxLength = 1000;

  useEffect(() => {
    if (lastStepRef.current !== stepId) {
      lastStepRef.current = stepId;
      setValue(initialValue || "");
    }
  }, [stepId, initialValue]);

  function stopEditorShortcut(event) {
    event.stopPropagation();
  }

  return (
    <div style={{ width: "100%" }}>
      <textarea
        className="adminTextArea"
        rows={7}
        maxLength={maxLength}
        style={{
          minHeight: "210px",
          width: "100%",
          resize: "vertical",
          lineHeight: "1.35"
        }}
        value={value}
        onChange={(event) => {
          const nextValue = event.target.value;
          setValue(nextValue);
          onDraftChange?.(stepId, nextValue);
        }}
        onBlur={() => onCommit?.(stepId, value)}
        onKeyDown={stopEditorShortcut}
        onKeyUp={stopEditorShortcut}
        onInput={stopEditorShortcut}
        onClick={stopEditorShortcut}
        onMouseDown={(event) => event.stopPropagation()}
        placeholder="New image prompt or correction. Example: show the installer checking the pan with a level; mortar belongs under the shower pan only; do not show mortar on top of the finished shower floor."
      />
      <div style={{ marginTop: "6px", fontSize: "0.78rem", color: "#666", textAlign: "right" }}>
        {value.length}/{maxLength} characters
      </div>
    </div>
  );
}

function QcDraftField({ as = "input", className = "", value = "", onDraftChange, onCommit, placeholder = "", fieldKey = "" }) {
  const cacheKey = fieldKey || `${className}-${placeholder}`;
  const initialDraftValue = qcDraftValueCache.has(cacheKey) ? qcDraftValueCache.get(cacheKey) : value || "";
  const editingRef = useRef(false);
  const fieldRef = useRef(null);
  const cacheKeyRef = useRef(cacheKey);
  const Field = as;

  useEffect(() => {
    if (cacheKeyRef.current === cacheKey) {
      return;
    }

    cacheKeyRef.current = cacheKey;
    editingRef.current = false;
    const nextValue = qcDraftValueCache.has(cacheKey) ? qcDraftValueCache.get(cacheKey) : value || "";
    qcDraftValueCache.set(cacheKey, nextValue);
    if (fieldRef.current) {
      fieldRef.current.value = nextValue;
    }
  }, [cacheKey, value]);

  function commitCurrentValue(target) {
    const nextValue = target?.value ?? qcDraftValueCache.get(cacheKey) ?? "";
    editingRef.current = false;
    qcDraftValueCache.set(cacheKey, nextValue);
    onCommit?.(nextValue);
  }

  function stopEditorShortcut(event) {
    event.stopPropagation();
    if (as !== "textarea" && event.key === "Enter") {
      event.preventDefault();
      commitCurrentValue(event.currentTarget);
      event.currentTarget.blur();
    }
  }

  return (
    <Field
      ref={fieldRef}
      className={className}
      defaultValue={initialDraftValue}
      onFocus={() => {
        editingRef.current = true;
      }}
      onChange={(event) => {
        const nextValue = event.target.value;
        qcDraftValueCache.set(cacheKey, nextValue);
        onDraftChange?.(nextValue);
      }}
      onBlur={(event) => commitCurrentValue(event.currentTarget)}
      onKeyDownCapture={stopEditorShortcut}
      onKeyDown={stopEditorShortcut}
      onKeyUp={stopEditorShortcut}
      onClickCapture={stopEditorShortcut}
      onClick={(event) => event.stopPropagation()}
      onMouseDownCapture={(event) => event.stopPropagation()}
      onMouseDown={(event) => event.stopPropagation()}
      onPointerDown={(event) => event.stopPropagation()}
      spellCheck={as === "textarea"}
      wrap={as === "textarea" ? "soft" : undefined}
      placeholder={placeholder}
    />
  );
}

function QcImageDirectionModal({ editor, step, generating, onClose, onDraftChange, onApply, onApplyAndGenerate }) {
  const [value, setValue] = useState(editor.value || "");

  function stopModalEditorEvent(event) {
    event.stopPropagation();
  }

  return (
    <div
      className="qcDirectionOverlay"
      role="dialog"
      aria-modal="true"
      aria-label="Edit image direction"
      onKeyDownCapture={stopModalEditorEvent}
      onKeyUpCapture={stopModalEditorEvent}
      onClick={stopModalEditorEvent}
      onMouseDown={stopModalEditorEvent}
      onPointerDown={stopModalEditorEvent}
    >
      <div className="qcDirectionDialog">
        <div className="qcDirectionHeader">
          <div>
            <strong>{step?.imageLabel || `Step ${editor.stepIndex + 1}`}</strong>
            <span>{step?.instruction || "Image direction"}</span>
          </div>
          <button className="secondaryButton compactButton" onClick={onClose}>
            Close
          </button>
        </div>
        <textarea
          className="qcDirectionModalTextarea"
          value={value}
          onChange={(event) => {
            const nextValue = event.target.value;
            setValue(nextValue);
            onDraftChange(nextValue);
          }}
          onKeyDownCapture={stopModalEditorEvent}
          onKeyDown={stopModalEditorEvent}
          onKeyUp={stopModalEditorEvent}
          onClick={stopModalEditorEvent}
          onMouseDown={stopModalEditorEvent}
          onPointerDown={stopModalEditorEvent}
          placeholder={IMAGE_DIRECTION_PLACEHOLDER}
          autoFocus
          spellCheck
        />
        <div className="qcDirectionActions">
          <button className="secondaryButton" onClick={onClose}>
            Cancel
          </button>
          <button className="secondaryButton" onClick={() => onApply(value)}>
            Apply
          </button>
          <button
            className="startButton"
            onClick={() => onApplyAndGenerate(value)}
            disabled={generating}
          >
            Apply + Generate
          </button>
        </div>
      </div>
    </div>
  );
}

function StepImageReview({ step }) {
  const hasPending = Boolean(step.pendingImageUrl);

  if (!hasPending) {
    return (
      <div>
        <img
          src={apiAssetUrl(step.imageUrl)}
          alt={step.imageLabel || `Step ${step.id}`}
          style={{
            width: "100%",
            maxHeight: "190px",
            objectFit: "cover",
            borderRadius: "12px",
            border: "1px solid rgba(0,0,0,0.1)"
          }}
        />
      </div>
    );
  }

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: "10px",
        alignItems: "start",
        marginBottom: "10px"
      }}
    >
      <div>
        <div style={{ fontWeight: 900, fontSize: "0.82rem", marginBottom: "5px" }}>
          CURRENT IMAGE
        </div>
        <img
          src={apiAssetUrl(step.imageUrl)}
          alt={step.imageLabel || `Step ${step.id}`}
          style={{
            width: "100%",
            maxHeight: "165px",
            objectFit: "cover",
            borderRadius: "12px",
            border: "1px solid rgba(0,0,0,0.15)",
            opacity: 0.82
          }}
        />
      </div>
      <div>
        <div style={{ fontWeight: 900, fontSize: "0.82rem", marginBottom: "5px", color: "#1d4ed8" }}>
          NEW CANDIDATE
        </div>
        <img
          src={apiAssetUrl(step.pendingImageUrl)}
          alt={`Candidate for step ${step.id}`}
          style={{
            width: "100%",
            maxHeight: "165px",
            objectFit: "cover",
            borderRadius: "12px",
            border: "3px solid rgba(37,99,235,0.55)",
            boxShadow: "0 0 0 3px rgba(37,99,235,0.12)"
          }}
        />
        <div style={{ marginTop: "6px", fontSize: "0.78rem", color: "#555", lineHeight: 1.25 }}>
          Review this candidate, then use the buttons below.
        </div>
      </div>
    </div>
  );
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
  const [selectedBranchId, setSelectedBranchId] = useState("");
  const [selectedBranchQuery, setSelectedBranchQuery] = useState("");
  const [selectedBrand, setSelectedBrand] = useState("");
  const [selectedModel, setSelectedModel] = useState("");
  const [loading, setLoading] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [activeHotspot, setActiveHotspot] = useState(null);
  const [complete, setComplete] = useState(false);

  const [adminStatus, setAdminStatus] = useState(null);
  const [adminMessage, setAdminMessage] = useState("");
  const [adminTokenValue, setAdminTokenValue] = useState(() => window.localStorage.getItem(ADMIN_TOKEN_STORAGE_KEY) || "");
  const [adminTokenStatus, setAdminTokenStatus] = useState(() => (
    window.localStorage.getItem(ADMIN_TOKEN_STORAGE_KEY) ? "Saved" : "Not saved"
  ));
  const [bulkQueries, setBulkQueries] = useState("");
  const [bulkCatalog, setBulkCatalog] = useState("");
  const [catalogBrand, setCatalogBrand] = useState("");
  const [catalogCategory, setCatalogCategory] = useState("");
  const [catalogModels, setCatalogModels] = useState("");
  const [discoverTopModels, setDiscoverTopModels] = useState(true);
  const [adminLoading, setAdminLoading] = useState(false);
  const [regeneratingStepId, setRegeneratingStepId] = useState(null);

  const [canonicalStatus, setCanonicalStatus] = useState(null);
  const [canonicalKey, setCanonicalKey] = useState("");
  const [canonicalStep, setCanonicalStep] = useState(1);
  const [canonicalFile, setCanonicalFile] = useState(null);

  const [overlayData, setOverlayData] = useState(null);
  const [specificQuery, setSpecificQuery] = useState("");
  const [tipsExpanded, setTipsExpanded] = useState(false);

  const [imageRegistry, setImageRegistry] = useState(null);
  const [promoteFilename, setPromoteFilename] = useState("");
  const [promoteCanonicalKey, setPromoteCanonicalKey] = useState("");
  const [promoteStepNumber, setPromoteStepNumber] = useState(1);

  const [buildStatus, setBuildStatus] = useState(null);
  const [taxonomyIndexStatus, setTaxonomyIndexStatus] = useState(null);
  const [walkthroughLibrary, setWalkthroughLibrary] = useState(null);
  const [libraryView, setLibraryView] = useState("stored");
  const [libraryFilter, setLibraryFilter] = useState("all");
  const [librarySearch, setLibrarySearch] = useState("");
  const [libraryMessage, setLibraryMessage] = useState("");
  const [libraryLoading, setLibraryLoading] = useState(false);
  const [libraryRebuilding, setLibraryRebuilding] = useState(false);
  const [visitorLog, setVisitorLog] = useState(null);
  const [visitorLoading, setVisitorLoading] = useState(false);
  const [visitorStartDate, setVisitorStartDate] = useState("");
  const [visitorEndDate, setVisitorEndDate] = useState(todayDateInputValue());
  const sessionStartedAtRef = useRef(Date.now());
  const lastVisitorQueryRef = useRef("");
  const lastVisitorWalkthroughIdRef = useRef("");

  const [bulkJobList, setBulkJobList] = useState(null);
  const [walkthroughList, setWalkthroughList] = useState([]);
  const [selectedAdminWalkthrough, setSelectedAdminWalkthrough] = useState(null);
  const [repairCorrections, setRepairCorrections] = useState({});
  const repairCorrectionRefs = useRef({});
  const [editorDraft, setEditorDraft] = useState(null);
  const [editorDirty, setEditorDirty] = useState(false);
  const [editorSaving, setEditorSaving] = useState(false);
  const [adminPanels, setAdminPanels] = useState({
    qc: true,
    visualMigration: true,
    library: true,
    visitors: true,
    catalog: false,
    status: false,
    activity: false,
    advanced: false
  });
  const [qcFilter, setQcFilter] = useState("draft");
  const [qcExpandedId, setQcExpandedId] = useState("");
  const [qcWalkthroughs, setQcWalkthroughs] = useState({});
  const [qcChanges, setQcChanges] = useState({});
  const [qcSaving, setQcSaving] = useState(false);
  const [qcImageGenerating, setQcImageGenerating] = useState({});
  const [qcAllImagesGenerating, setQcAllImagesGenerating] = useState({});
  const [imageDirectionEditor, setImageDirectionEditor] = useState(null);
  const [visualMigrationReport, setVisualMigrationReport] = useState(null);
  const [visualMigrationLoading, setVisualMigrationLoading] = useState(false);
  const [catalogPipelineStatus, setCatalogPipelineStatus] = useState(null);
  const [catalogPipelineRunning, setCatalogPipelineRunning] = useState("");
  const [productPackageBrand, setProductPackageBrand] = useState("Niagara");
  const [productPackageModel, setProductPackageModel] = useState("Original Stealth");
  const [productPackageCategory, setProductPackageCategory] = useState("toilet");
  const [productPackageUrl, setProductPackageUrl] = useState("https://niagaracorp.com/products/original-stealth-handle-round/");
  const [productPackageRunning, setProductPackageRunning] = useState(false);
  const [productPackageResult, setProductPackageResult] = useState(null);
  const [photoDiagnostics, setPhotoDiagnostics] = useState({});
  const [photoOverrideUrls, setPhotoOverrideUrls] = useState({});
  const [photoActionKey, setPhotoActionKey] = useState("");

  const currentStep = walkthrough?.steps?.[stepIndex];
  const availableBrands = productOptions?.brands || [];
  const branchOptions = productOptions?.branches || [];
  const selectedBrandRecord = availableBrands.find(
    (item) => item.brand === selectedBrand
  );
  const availableModels = selectedBrandRecord?.models || [];
  const currentModelTips = overlayData?.installation_tips || overlayData?.overlays || [];

  function getAdminToken(promptLabel = "continue") {
    const cached = adminTokenValue || window.localStorage.getItem(ADMIN_TOKEN_STORAGE_KEY);
    if (cached) {
      return cached;
    }

    setAdminMessage(`Enter the admin token above to ${promptLabel}.`);
    return "";
  }

  function clearAdminToken() {
    window.localStorage.removeItem(ADMIN_TOKEN_STORAGE_KEY);
    setAdminTokenValue("");
    setAdminTokenStatus("Not saved");
  }

  function saveAdminToken() {
    const token = adminTokenValue.trim();
    if (!token) {
      clearAdminToken();
      setAdminMessage("Admin token cleared.");
      setAdminTokenStatus("Not saved");
      return;
    }

    window.localStorage.setItem(ADMIN_TOKEN_STORAGE_KEY, token);
    setAdminTokenValue(token);
    setAdminTokenStatus("Saved");
    setAdminMessage("Admin token saved for this browser.");
  }

  function preserveScrollAfter(updateAction) {
    const scrollY = window.scrollY;
    return Promise.resolve(typeof updateAction === "function" ? updateAction() : updateAction).finally(() => {
      window.requestAnimationFrame(() => window.scrollTo({ top: scrollY, left: 0 }));
    });
  }

  function logVisitorEvent(event, overrides = {}) {
    const payload = {
      event,
      query: overrides.query ?? lastVisitorQueryRef.current,
      walkthrough_id: overrides.walkthrough_id ?? lastVisitorWalkthroughIdRef.current,
      path: window.location.pathname,
      time_spent_seconds: overrides.time_spent_seconds ?? 0,
      metadata: overrides.metadata || {}
    };
    const body = JSON.stringify(payload);

    try {
      if (navigator.sendBeacon) {
        const blob = new Blob([body], { type: "application/json" });
        navigator.sendBeacon(`${API_URL}/visitor/event`, blob);
        return;
      }
    } catch (error) {
      console.error(error);
    }

    fetch(`${API_URL}/visitor/event`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      keepalive: true
    }).catch((error) => console.error(error));
  }

  async function loadVisitors(tokenOverride = "") {
    const token = tokenOverride || getAdminToken("load visitor logs");
    if (!token) {
      setAdminMessage("Visitor log load cancelled. No admin token was entered.");
      return;
    }

    const params = new URLSearchParams({
      limit: "500"
    });
    if (visitorStartDate) params.set("start_date", visitorStartDate);
    if (visitorEndDate) params.set("end_date", visitorEndDate);

    setVisitorLoading(true);

    try {
      const response = await fetch(`${API_URL}/admin/visitors?${params.toString()}`, {
        headers: { "X-Admin-Token": token },
        cache: "no-store"
      });
      const data = await response.json();

      if (!response.ok) {
        clearAdminToken();
        throw new Error(data.detail || data.error || "Visitor log failed.");
      }

      setVisitorLog(data);
      setAdminMessage(`Visitor log loaded: ${data.summary?.event_count || 0} event(s).`);
    } catch (error) {
      console.error(error);
      setAdminMessage(`Could not load visitor log: ${error.message}`);
    } finally {
      setVisitorLoading(false);
    }
  }

  async function exportVisitorsCsv() {
    const token = getAdminToken("export visitor logs");
    if (!token) {
      setAdminMessage("Visitor export cancelled. No admin token was entered.");
      return;
    }

    const params = new URLSearchParams();
    if (visitorStartDate) params.set("start_date", visitorStartDate);
    if (visitorEndDate) params.set("end_date", visitorEndDate);

    setVisitorLoading(true);

    try {
      const response = await fetch(`${API_URL}/admin/visitors.csv?${params.toString()}`, {
        headers: { "X-Admin-Token": token },
        cache: "no-store"
      });

      if (!response.ok) {
        const text = await response.text();
        clearAdminToken();
        throw new Error(text || "Visitor export failed.");
      }

      const blob = await response.blob();
      const downloadUrl = URL.createObjectURL(blob);
      const dateLabel = `${visitorStartDate || "begin"}-to-${visitorEndDate || "latest"}`;
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = `rocketsurgery-visitors-${dateLabel}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(downloadUrl);
      setAdminMessage(`Visitor CSV exported for ${dateLabel}.`);
    } catch (error) {
      console.error(error);
      setAdminMessage(`Could not export visitor CSV: ${error.message}`);
    } finally {
      setVisitorLoading(false);
    }
  }

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
    const resolvedQuery = finalQuery || "James Hardie siding nailing schedule";
    lastVisitorQueryRef.current = resolvedQuery;
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
          query: resolvedQuery
        })
      });

      const data = await response.json();

      setWalkthrough(data);
      lastVisitorWalkthroughIdRef.current = data?.walkthrough_id || "";

      logVisitorEvent("walkthrough_loaded", {
        query: resolvedQuery,
        walkthrough_id: data?.walkthrough_id || "",
        metadata: {
          step_count: data?.steps?.length || 0
        }
      });

      await fetchOverlay(resolvedQuery);

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
    setSpecificQuery("");
    setTipsExpanded(false);
    }
  }


  async function startWalkthrough() {
    const trimmedQuery = query.trim() || "generic installation walkthrough";

    setLoading(true);
    setInstallMode("");
    setSelectedBrand("");
    setSelectedModel("");
    setSelectedBranchId("");
    setSelectedBranchQuery("");
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
    fetchWalkthrough(selectedBranchQuery || query.trim() || "generic installation walkthrough");
  }

  async function continueSpecific() {
    const finalQuery = buildSpecificQuery(selectedBranchQuery || query, selectedBrand, selectedModel);
    setInstallMode("specific");
    setSpecificQuery(finalQuery);
    setTipsExpanded(false);
    setLoading(true);

    try {
      await fetchOverlay(finalQuery);
      setClarifying(false);
      setStarted(false);
      setScreen("briefing");
    } catch (error) {
      console.error(error);
      alert("Could not load model-specific briefing.");
    } finally {
      setLoading(false);
    }
  }

  function proceedSpecificInstall() {
    fetchWalkthrough(specificQuery || buildSpecificQuery(query, selectedBrand, selectedModel));
  }

  function newJob() {
    window.speechSynthesis.cancel();
    logVisitorEvent("new_job", {
      time_spent_seconds: Math.round((Date.now() - sessionStartedAtRef.current) / 1000)
    });
    setScreen("home");
    setQuery("");
    setWalkthrough(null);
    setStarted(false);
    setClarifying(false);
    setInstallMode("");
    setSelectedBranchId("");
    setSelectedBranchQuery("");
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
    loadAdminWalkthroughs();
    loadCatalogPipelineStatus();
    const cachedToken = window.localStorage.getItem(ADMIN_TOKEN_STORAGE_KEY);
    if (cachedToken) {
      setAdminTokenValue(cachedToken);
      loadWalkthroughLibrary(cachedToken);
      loadVisitors(cachedToken);
    }
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
    logVisitorEvent("back_to_home", {
      time_spent_seconds: Math.round((Date.now() - sessionStartedAtRef.current) / 1000)
    });
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
      setRegeneratingStepId(null);
    }
  }


  async function loadCatalogPipelineStatus() {
    setAdminMessage("Loading catalog pipeline status...");

    try {
      const response = await fetch(`${API_URL}/admin/catalog/toilet-status`, {
        cache: "no-store"
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.status || "Could not load catalog pipeline status.");
      }

      setCatalogPipelineStatus(data);
      setAdminMessage(`Catalog pipelines loaded: ${(data.items || []).length} models.`);
    } catch (error) {
      console.error(error);
      setAdminMessage(`Catalog pipeline status failed: ${error.message}`);
    }
  }

  async function runCatalogPipeline(item, pipeline = "all") {
    const key = `${item.brand}-${item.model}-${pipeline}`;
    setCatalogPipelineRunning(key);
    setAdminMessage(`Running ${pipeline} pipeline for ${item.brand} ${item.model}...`);

    const productPageUrl = item.photo?.product_page_url || item.product_page_url || "";
    const useProductPackageBuilder = pipeline === "all" && productPageUrl;

    const endpoint = useProductPackageBuilder
      ? "/admin/catalog/build-product-page-package"
      : pipeline === "photo"
        ? "/admin/catalog/fetch-product-photo"
        : pipeline === "manual"
          ? "/admin/catalog/fetch-install-manual"
          : pipeline === "overlay"
            ? "/admin/catalog/build-overlay-package"
            : "/admin/catalog/run-model-pipelines";

    const payload = useProductPackageBuilder
      ? {
          category: item.category || "toilet",
          brand: item.brand,
          model: item.model,
          product_page_url: productPageUrl
        }
      : {
          category: item.category || "toilet",
          brand: item.brand,
          model: item.model
        };

    try {
      const response = await fetch(`${API_URL}${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        cache: "no-store",
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.status || "Pipeline request failed.");
      }

      if (data?.product?.photo_url) {
        setPhotoDiagnostics((current) => ({
          ...current,
          [catalogItemKey(item)]: {
            ...(current[catalogItemKey(item)] || {}),
            cached_photo_url: data.product.photo_url,
            remote_photo_url: data.product.remote_photo_url || "",
            download_status: "cached",
            selected_candidate: data.product.remote_photo_url || ""
          }
        }));
      }

      setAdminMessage(`${item.brand} ${item.model}: ${pipeline} pipeline finished with status ${data.status}.`);
      await loadCatalogPipelineStatus();
    } catch (error) {
      console.error(error);
      setAdminMessage(`${item.brand} ${item.model}: ${pipeline} pipeline failed — ${error.message}`);
    } finally {
      setCatalogPipelineRunning("");
    }
  }


  function catalogItemKey(item) {
    return `${item.brand}__${item.model}`.replace(/\s+/g, "_");
  }

  async function diagnoseProductPhoto(item) {
    const key = catalogItemKey(item);
    setPhotoActionKey(`${key}-diagnose`);
    setAdminMessage(`Diagnosing photo discovery for ${item.brand} ${item.model}...`);

    try {
      const response = await fetch(`${API_URL}/admin/catalog/photo-diagnostics`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
        body: JSON.stringify({
          category: item.category || "toilet",
          brand: item.brand,
          model: item.model
        })
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || data.error || data.status || "Photo diagnostics failed.");
      }
      setPhotoDiagnostics((current) => ({ ...current, [key]: data }));
      const count = Array.isArray(data.image_candidates) ? data.image_candidates.length : 0;
      const cached = Boolean(data.cached_photo_url || data.download_status === "cached");
      setAdminMessage(
        cached
          ? `${item.brand} ${item.model}: photo cached from ${count} discovered candidate(s).`
          : `${item.brand} ${item.model}: found ${count} image candidate(s). ${data.failure_reason || ""}`.trim()
      );
      if (cached) {
        await loadCatalogPipelineStatus();
      }
    } catch (error) {
      console.error(error);
      setPhotoDiagnostics((current) => ({
        ...current,
        [key]: { status: "failed", failure_reason: error.message, image_candidates: [] }
      }));
      setAdminMessage(`${item.brand} ${item.model}: photo diagnostics failed — ${error.message}`);
    } finally {
      setPhotoActionKey("");
    }
  }

  async function cacheProductPhotoFromUrl(item) {
    const key = catalogItemKey(item);
    const imageUrl = (photoOverrideUrls[key] || "").trim();

    if (!imageUrl) {
      setAdminMessage("Paste a manufacturer-hosted image URL before caching the photo.");
      return;
    }

    setPhotoActionKey(`${key}-cache`);
    setAdminMessage(`Caching photo for ${item.brand} ${item.model}...`);

    try {
      const response = await fetch(`${API_URL}/admin/catalog/cache-photo-url`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
        body: JSON.stringify({
          category: item.category || "toilet",
          brand: item.brand,
          model: item.model,
          image_url: imageUrl
        })
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || data.error || data.status || "Could not cache photo.");
      }
      setProductPackageResult(data);
      setAdminMessage(`${item.brand} ${item.model}: photo cache status ${data.status}.`);
      await loadCatalogPipelineStatus();
      await diagnoseProductPhoto(item);
    } catch (error) {
      console.error(error);
      setAdminMessage(`${item.brand} ${item.model}: cache photo failed — ${error.message}`);
    } finally {
      setPhotoActionKey("");
    }
  }


  async function cacheProductPhotoCandidate(item, candidateUrl) {
    const key = catalogItemKey(item);
    const imageUrl = (candidateUrl || "").trim();

    if (!imageUrl) {
      setAdminMessage("No image candidate was selected.");
      return;
    }

    setPhotoActionKey(`${key}-select`);
    setAdminMessage(`Saving selected photo for ${item.brand} ${item.model}...`);

    try {
      const response = await fetch(`${API_URL}/admin/catalog/cache-photo-url`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
        body: JSON.stringify({
          category: item.category || "toilet",
          brand: item.brand,
          model: item.model,
          image_url: imageUrl
        })
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || data.error || data.status || "Could not cache selected photo.");
      }

      const localUrl = data?.photo?.local_url || data?.product?.photo_url || "";
      setPhotoDiagnostics((current) => ({
        ...current,
        [key]: {
          ...(current[key] || {}),
          cached_photo_url: localUrl,
          download_status: data.status || "cached",
          selected_candidate: imageUrl,
          failure_reason: data?.photo?.error || ""
        }
      }));
      setPhotoOverrideUrls((current) => ({ ...current, [key]: "" }));
      setAdminMessage(`${item.brand} ${item.model}: selected photo saved.`);
      await loadCatalogPipelineStatus();
      await diagnoseProductPhoto(item);
    } catch (error) {
      console.error(error);
      setAdminMessage(`${item.brand} ${item.model}: selected photo failed — ${error.message}`);
    } finally {
      setPhotoActionKey("");
    }
  }


  async function rejectProductPhotoCandidates(item) {
    const key = catalogItemKey(item);
    const diagnostic = photoDiagnostics[key] || {};
    const candidateCount = Array.isArray(diagnostic.image_candidates) ? diagnostic.image_candidates.length : 0;

    const ok = window.confirm(
      `Reject all discovered photo candidates for ${item.brand} ${item.model}?\n\nThis clears the cached photo for this product and prevents the current candidate set from being auto-selected again. You can still paste a manufacturer image URL afterward.`
    );

    if (!ok) return;

    setPhotoActionKey(`${key}-reject`);
    setAdminMessage(`Rejecting discovered photos for ${item.brand} ${item.model}...`);

    try {
      const response = await fetch(`${API_URL}/admin/catalog/reject-photo-candidates`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
        body: JSON.stringify({
          category: item.category || "toilet",
          brand: item.brand,
          model: item.model
        })
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || data.error || data.status || "Could not reject photo candidates.");
      }
      setPhotoDiagnostics((current) => ({
        ...current,
        [key]: {
          ...(current[key] || {}),
          cached_photo_url: "",
          download_status: "rejected",
          failure_reason: `Rejected ${data.rejected_count || candidateCount || 0} image candidate(s). Paste a manufacturer image URL to override.`,
          rejected_count: data.rejected_count || candidateCount || 0,
          image_candidates: []
        }
      }));
      setAdminMessage(`${item.brand} ${item.model}: rejected ${data.rejected_count || candidateCount || 0} discovered photo candidate(s).`);
      await loadCatalogPipelineStatus();
    } catch (error) {
      console.error(error);
      setAdminMessage(`${item.brand} ${item.model}: reject candidates failed — ${error.message}`);
    } finally {
      setPhotoActionKey("");
    }
  }


  async function buildProductPagePackage() {
    const brand = productPackageBrand.trim();
    const model = productPackageModel.trim();
    const url = productPackageUrl.trim();
    const category = productPackageCategory.trim() || "toilet";

    if (!brand || !model || !url) {
      setAdminMessage("Enter brand, model, and manufacturer product page URL first.");
      return;
    }

    setProductPackageRunning(true);
    setProductPackageResult(null);
    setAdminMessage(`Building product package for ${brand} ${model}...`);

    try {
      const response = await fetch(`${API_URL}/admin/catalog/build-product-page-package`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          category,
          brand,
          model,
          product_page_url: url
        })
      });

      const text = await response.text();
      let data;
      try {
        data = JSON.parse(text);
      } catch {
        data = { raw: text };
      }

      if (!response.ok) {
        throw new Error(data.detail || data.error || data.status || "Product package build failed.");
      }

      setProductPackageResult(data);
      const confidence = data.product?.confidence || "UNKNOWN";
      const photo = data.product?.photo_url ? "photo cached" : "photo missing";
      const manual = data.product?.manual_url ? "manual cached" : "manual missing";
      setAdminMessage(`${brand} ${model} package built: ${photo}, ${manual}, confidence ${confidence}.`);
      await loadCatalogPipelineStatus();
    } catch (error) {
      console.error(error);
      setAdminMessage(`Product package build failed: ${error.message}`);
      setProductPackageResult({ status: "failed", error: error.message });
    } finally {
      setProductPackageRunning(false);
    }
  }


  async function testBuildNiagaraStealth() {
    setProductPackageRunning(true);
    setProductPackageResult(null);
    setAdminMessage("Running verbose Niagara Original Stealth test build...");

    try {
      const response = await fetch(`${API_URL}/admin/catalog/test-build-niagara-stealth`, {
        method: "POST",
        cache: "no-store"
      });

      const text = await response.text();
      let data;
      try {
        data = JSON.parse(text);
      } catch {
        data = { status: "non_json_response", raw: text };
      }

      if (!response.ok) {
        throw new Error(data.detail || data.error || data.status || `HTTP ${response.status}`);
      }

      setProductPackageResult(data);
      const imageCount = Array.isArray(data.image_candidates) ? data.image_candidates.length : 0;
      const pdfCount = Array.isArray(data.pdf_candidates) ? data.pdf_candidates.length : 0;
      const imageFiles = Array.isArray(data.files?.images) ? data.files.images.length : 0;
      const manualFiles = Array.isArray(data.files?.manuals) ? data.files.manuals.length : 0;
      setAdminMessage(
        `Niagara test build: ${data.status}. Found ${imageCount} image candidates, ${pdfCount} PDF candidates; wrote ${imageFiles} image file(s), ${manualFiles} manual file(s).`
      );
      await loadCatalogPipelineStatus();
    } catch (error) {
      console.error(error);
      setAdminMessage(`Niagara test build failed: ${error.message}`);
      setProductPackageResult({ status: "failed", error: error.message });
    } finally {
      setProductPackageRunning(false);
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


  async function rebuildWalkthroughIndex(tokenOverride = "") {
    const token = tokenOverride || getAdminToken("sift existing walkthroughs");
    if (!token) {
      setAdminMessage("Walkthrough indexing cancelled. No token was entered.");
      setLibraryMessage("Rebuild cancelled. No admin token was entered.");
      return;
    }

    setLibraryRebuilding(true);
    setLibraryMessage("Rebuilding walkthrough index from persistent storage...");

    try {
      const response = await fetch(
        `${API_URL}/admin/rebuild-walkthrough-index`,
        {
          method: "POST",
          headers: {
            "X-Admin-Token": token
          }
        }
      );

      const data = await response.json();

      if (!response.ok) {
        clearAdminToken();
        throw new Error(data.detail || data.error || "Walkthrough index rebuild failed.");
      }

      setTaxonomyIndexStatus(data);
      const message =
        `Sifted ${data.stored_walkthrough_count || 0} stored walkthroughs. ` +
        `${data.taxonomy_entries_with_existing_walkthroughs || 0} taxonomy entries now have existing walkthrough matches; ` +
        `${data.prospective_taxonomy_entries_without_existing_walkthroughs || 0} remain prospective.`;
      setAdminMessage(message);
      setLibraryMessage(message);
      loadBuildStatus();
      loadAdminWalkthroughs();
      await loadWalkthroughLibrary(token);
    } catch (error) {
      console.error(error);
      setAdminMessage(`Could not rebuild walkthrough index: ${error.message}`);
      setLibraryMessage(`Rebuild failed: ${error.message}`);
    } finally {
      setLibraryRebuilding(false);
    }
  }


  async function loadWalkthroughLibrary(tokenOverride = "") {
    const token = tokenOverride || getAdminToken("load the walkthrough library");
    if (!token) {
      setAdminMessage("Walkthrough library cancelled. No admin token was entered.");
      setLibraryMessage("Library load cancelled. No admin token was entered.");
      return;
    }

    setLibraryLoading(true);
    setLibraryMessage("Loading walkthrough library...");

    try {
      const response = await fetch(`${API_URL}/admin/walkthrough-library?limit=1000`, {
        headers: {
          "X-Admin-Token": token
        }
      });
      const data = await response.json();

      if (!response.ok) {
        clearAdminToken();
        throw new Error(data.detail || data.error || "Walkthrough library failed.");
      }

      setWalkthroughLibrary(data);
      const summary = data.summary || {};
      setTaxonomyIndexStatus((previous) => ({
        ...(previous || {}),
        ...summary
      }));
      const message = `Library loaded: ${summary.stored_walkthrough_count || 0} stored, ${summary.prospective_taxonomy_entries_without_existing_walkthroughs || 0} prospective.`;
      setAdminMessage(message);
      setLibraryMessage(message);
    } catch (error) {
      console.error(error);
      setAdminMessage(`Could not load walkthrough library: ${error.message}`);
      setLibraryMessage(`Library load failed: ${error.message}`);
    } finally {
      setLibraryLoading(false);
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
        repairCorrectionRefs.current = {};
        setRepairCorrections({});
        setEditorDraft(JSON.parse(JSON.stringify(data.walkthrough)));
        setEditorDirty(false);
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


  function reviewStatusFor(item) {
    return String(item?.review_status || "draft").toLowerCase();
  }


  function qcItemId(item) {
    return item?.storage_walkthrough_id || item?.walkthrough_id || "";
  }


  function isDraftQcItem(item) {
    const status = reviewStatusFor(item);
    return !["approved", "deleted", "deprecated"].includes(status);
  }


  function qcListItems() {
    return (walkthroughList || []).filter((item) => {
      if (qcChanges[qcItemId(item)]?.action === "delete") {
        return false;
      }

      return qcFilter === "approved"
        ? reviewStatusFor(item) === "approved"
        : isDraftQcItem(item);
    });
  }


  function libraryStoredItems() {
    const query = librarySearch.trim().toLowerCase();

    return (walkthroughLibrary?.stored_walkthroughs || []).filter((item) => {
      if (libraryFilter === "matched" && item.coverage_status !== "matched_taxonomy") {
        return false;
      }
      if (libraryFilter === "unmatched" && item.coverage_status !== "unmatched_existing") {
        return false;
      }
      if (libraryFilter === "branch" && !item.requires_branch_selection) {
        return false;
      }
      if (libraryFilter === "draft" && reviewStatusFor(item) !== "draft") {
        return false;
      }
      if (!query) {
        return true;
      }

      return [
        item.title,
        item.walkthrough_id,
        item.canonical_query,
        item.taxonomy_walkthrough_id,
        item.category,
        ...(item.aliases || [])
      ].join(" ").toLowerCase().includes(query);
    });
  }


  function libraryProspectiveItems() {
    const query = librarySearch.trim().toLowerCase();

    return (walkthroughLibrary?.prospective_walkthroughs || []).filter((item) => {
      if (libraryFilter === "branch" && !item.requires_branch_selection) {
        return false;
      }
      if (!query) {
        return true;
      }

      return [
        item.title,
        item.taxonomy_walkthrough_id,
        item.canonical_query,
        item.category
      ].join(" ").toLowerCase().includes(query);
    });
  }


  async function toggleQcWalkthrough(walkthroughId) {
    if (qcExpandedId === walkthroughId) {
      setQcExpandedId("");
      return;
    }

    setQcExpandedId(walkthroughId);

    if (qcWalkthroughs[walkthroughId]) {
      return;
    }

    setAdminLoading(true);
    try {
      const response = await fetch(`${API_URL}/admin/walkthroughs/${encodeURIComponent(walkthroughId)}`);
      const data = await response.json();

      if (data.walkthrough) {
        setQcWalkthroughs((previous) => ({
          ...previous,
          [walkthroughId]: JSON.parse(JSON.stringify(data.walkthrough))
        }));
      } else {
        setAdminMessage("Walkthrough not found.");
      }
    } catch (error) {
      console.error(error);
      setAdminMessage("Could not load QC walkthrough.");
    } finally {
      setAdminLoading(false);
    }
  }


  function stageQcChange(walkthroughId, action, steps = null, title = "", announce = true) {
    setQcChanges((previous) => {
      const existing = previous[walkthroughId] || {};
      return {
        ...previous,
        [walkthroughId]: {
          ...existing,
          action,
          steps: steps || existing.steps || []
        }
      };
    });
    if (announce) {
      const labels = {
        approve: "Approval staged",
        save: "Save staged",
        delete: "Delete staged"
      };
      setAdminMessage(`${labels[action] || "Change staged"} for ${title || walkthroughId}. Click Save All to apply it.`);
    }
  }


  function updateQcMetadata(walkthroughId, field, value, options = {}) {
    const { announce = true } = options;
    const draft = qcWalkthroughs[walkthroughId];
    if (!draft) {
      return;
    }

    const updatedDraft = {
      ...draft,
      [field]: value
    };

    setQcWalkthroughs((previous) => ({
      ...previous,
      [walkthroughId]: updatedDraft
    }));
    setWalkthroughList((previous) => previous.map((item) => (
      qcItemId(item) === walkthroughId
        ? {
            ...item,
            title: field === "title" ? value : item.title,
            query: field === "query" ? value : item.query
          }
        : item
    )));
    setQcChanges((previous) => {
      const existing = previous[walkthroughId] || {};
      return {
        ...previous,
        [walkthroughId]: {
          ...existing,
          action: existing.action || "save",
          steps: existing.steps || updatedDraft.steps || [],
          title: field === "title" ? value : existing.title,
          query: field === "query" ? value : existing.query,
          visual_template: field === "visual_template" ? value : existing.visual_template
        }
      };
    });
    if (announce) {
      setAdminMessage(`Metadata edit staged for ${updatedDraft.title || walkthroughId}. Click Save All to apply it.`);
    }
  }


  async function adoptApprovedMatch(walkthroughId) {
    const draft = qcWalkthroughs[walkthroughId];
    if (!draft) {
      setAdminMessage("Open the draft before adopting an approved match.");
      return;
    }

    const token = getAdminToken("adopt an approved walkthrough match");
    if (!token) {
      setAdminMessage("Approved match adoption cancelled. No admin token was entered.");
      return;
    }

    setQcSaving(true);
    try {
      const response = await fetch(`${API_URL}/admin/qc/adopt-approved-match`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Token": token
        },
        body: JSON.stringify({
          walkthrough_id: walkthroughId,
          walkthrough: draft
        })
      });
      const data = await response.json();

      if (!response.ok) {
        clearAdminToken();
        throw new Error(data.detail || data.error || "Could not adopt approved match.");
      }

      if (data.status !== "matched" || !data.walkthrough) {
        throw new Error(data.message || "No approved equivalent walkthrough was found.");
      }

      setQcWalkthroughs((previous) => ({
        ...previous,
        [walkthroughId]: JSON.parse(JSON.stringify(data.walkthrough))
      }));
      setQcChanges((previous) => ({
        ...previous,
        [walkthroughId]: {
          ...(previous[walkthroughId] || {}),
          action: previous[walkthroughId]?.action || "save",
          steps: data.walkthrough.steps || [],
          title: data.walkthrough.title,
          query: data.walkthrough.query
        }
      }));
      setAdminMessage(
        `Copied ${data.step_count || 0} steps and ${data.image_count || 0} image(s) from approved walkthrough "${data.approved_title || data.approved_walkthrough_id}". Review, then Save All or Stage Approve.`
      );
    } catch (error) {
      console.error(error);
      setAdminMessage(`Approved match adoption failed: ${error.message}`);
    } finally {
      setQcSaving(false);
    }
  }


  function renumberQcSteps(steps) {
    return (steps || []).map((step, idx) => {
      const stepNumber = idx + 1;
      const normalizeStepPrefix = (value) => {
        const text = String(value || "");
        if (!text) {
          return text;
        }
        if (/^step\s+\d+\s*:/i.test(text)) {
          return text.replace(/^step\s+\d+\s*:/i, `Step ${stepNumber}:`);
        }
        return text;
      };

      return {
        ...step,
        id: stepNumber,
        imageLabel: normalizeStepPrefix(step.imageLabel),
        instruction: normalizeStepPrefix(step.instruction)
      };
    });
  }


  function moveQcStep(walkthroughId, stepIndex, direction) {
    const draft = qcWalkthroughs[walkthroughId];
    if (!draft?.steps?.length) {
      return;
    }

    const steps = [...draft.steps];
    const nextIndex = stepIndex + direction;

    if (stepIndex < 0 || nextIndex < 0 || nextIndex >= steps.length) {
      return;
    }

    const [removed] = steps.splice(stepIndex, 1);
    steps.splice(nextIndex, 0, removed);
    const renumbered = renumberQcSteps(steps);

    setQcWalkthroughs((previous) => ({
      ...previous,
      [walkthroughId]: {
        ...draft,
        steps: renumbered
      }
    }));
    stageQcChange(walkthroughId, qcChanges[walkthroughId]?.action || "save", renumbered);
  }


  function updateQcStep(walkthroughId, stepIndex, field, value) {
    const draft = qcWalkthroughs[walkthroughId];
    if (!draft?.steps?.length) {
      return;
    }

    const updatedSteps = (draft.steps || []).map((step, index) => (
      index === stepIndex
        ? { ...step, [field]: value, imageStale: true }
        : step
    ));

    setQcWalkthroughs((previous) => ({
      ...previous,
      [walkthroughId]: {
        ...draft,
        steps: updatedSteps
      }
    }));
    stageQcChange(walkthroughId, qcChanges[walkthroughId]?.action || "save", updatedSteps, "", false);
  }


  function addQcStepAfter(walkthroughId, stepIndex = null) {
    const draft = qcWalkthroughs[walkthroughId];
    if (!draft) {
      return;
    }

    const steps = [...(draft.steps || [])];
    const insertIndex = stepIndex == null ? steps.length : stepIndex + 1;
    const templateNumber = insertIndex + 1;
    const newStep = {
      id: templateNumber,
      imageLabel: `Step ${templateNumber}: New step`,
      instruction: `Step ${templateNumber}: New step`,
      detail: "Describe the missing action here.",
      imagePrompt: "",
      imageStale: true
    };

    steps.splice(insertIndex, 0, newStep);
    const renumbered = renumberQcSteps(steps);

    setQcWalkthroughs((previous) => ({
      ...previous,
      [walkthroughId]: {
        ...draft,
        steps: renumbered
      }
    }));
    stageQcChange(walkthroughId, qcChanges[walkthroughId]?.action || "save", renumbered, "", false);
  }


  function deleteQcStep(walkthroughId, stepIndex) {
    const draft = qcWalkthroughs[walkthroughId];
    if (!draft?.steps?.length) {
      return;
    }

    const renumbered = (draft.steps || [])
      .filter((_, index) => index !== stepIndex)
      .map((step, idx) => ({ ...step, id: idx + 1 }));

    setQcWalkthroughs((previous) => ({
      ...previous,
      [walkthroughId]: {
        ...draft,
        steps: renumbered
      }
    }));
    stageQcChange(walkthroughId, qcChanges[walkthroughId]?.action || "save", renumbered, "", false);
  }

  function openImageDirectionEditor(walkthroughId, stepIndex) {
    const step = qcWalkthroughs[walkthroughId]?.steps?.[stepIndex];
    if (!step) {
      return;
    }

    const cacheKey = qcImageDirectionCacheKey(walkthroughId, stepIndex);
    setImageDirectionEditor({
      walkthroughId,
      stepIndex,
      cacheKey,
      value: qcDraftValueCache.has(cacheKey) ? qcDraftValueCache.get(cacheKey) : step.imageDirection || "",
      scrollY: window.scrollY
    });
  }

  function restoreImageDirectionEditorScroll(editor = imageDirectionEditor) {
    const scrollY = Number(editor?.scrollY);
    if (!Number.isFinite(scrollY)) {
      return;
    }
    window.requestAnimationFrame(() => window.scrollTo({ top: scrollY, left: 0 }));
  }

  function closeImageDirectionEditor() {
    const editor = imageDirectionEditor;
    setImageDirectionEditor(null);
    restoreImageDirectionEditorScroll(editor);
  }

  function cacheImageDirectionEditorValue(value) {
    if (!imageDirectionEditor) {
      return;
    }
    qcDraftValueCache.set(imageDirectionEditor.cacheKey, value);
  }

  function commitImageDirectionEditorValue(value) {
    if (!imageDirectionEditor) {
      return null;
    }

    const { walkthroughId, stepIndex, cacheKey } = imageDirectionEditor;
    qcDraftValueCache.set(cacheKey, value);
    updateQcStep(walkthroughId, stepIndex, "imageDirection", value);
    return { walkthroughId, stepIndex };
  }

  function applyImageDirectionEditor(value) {
    commitImageDirectionEditorValue(value);
    closeImageDirectionEditor();
  }

  function applyAndGenerateImageDirection(value) {
    const editor = imageDirectionEditor;
    const target = commitImageDirectionEditorValue(value);
    setImageDirectionEditor(null);
    restoreImageDirectionEditorScroll(editor);
    if (target) {
      window.setTimeout(() => generateQcStepImage(target.walkthroughId, target.stepIndex), 0);
    }
  }


  async function generateQcStepImage(walkthroughId, stepIndex) {
    const draft = qcWalkthroughs[walkthroughId];
    const step = draft?.steps?.[stepIndex];
    if (!draft || !step) {
      return;
    }
    const imageDirectionKey = qcImageDirectionCacheKey(walkthroughId, stepIndex);
    const latestImageDirection = qcDraftValueCache.has(imageDirectionKey)
      ? qcDraftValueCache.get(imageDirectionKey)
      : step.imageDirection || "";
    const stepForGeneration = {
      ...step,
      imageDirection: latestImageDirection,
      imageStale: true
    };

    const token = getAdminToken("generate a QC step image");
    if (!token) {
      setAdminMessage("Image generation cancelled. No admin token was entered.");
      return;
    }

    const key = `${walkthroughId}-${stepIndex}`;
    setQcImageGenerating((previous) => ({ ...previous, [key]: true }));
    setAdminMessage(`Generating image for step ${stepIndex + 1}...`);

    try {
      const controller = new AbortController();
      const timeoutId = window.setTimeout(() => controller.abort(), 240000);
      const response = await fetch(`${API_URL}/admin/qc/generate-step-image`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Token": token
        },
        signal: controller.signal,
        body: JSON.stringify({
          walkthrough_id: walkthroughId,
          title: draft.title || "",
          query: draft.query || "",
          step: stepForGeneration,
          image_direction: latestImageDirection,
          visual_template: draft.visual_template || "",
          visual_assets: draft.visual_assets || {}
        })
      });
      window.clearTimeout(timeoutId);
      const data = await response.json();

      if (!response.ok) {
        if (response.status === 401) {
          clearAdminToken();
        }
        throw new Error(data.detail || data.error || "Image generation failed.");
      }

      const updatedSteps = (draft.steps || []).map((item, index) => (
        index === stepIndex
          ? {
              ...item,
              imageUrl: cacheBustUrl(data.image_url),
              imagePrompt: data.image_prompt,
              imageDirection: latestImageDirection,
              imageStale: false
            }
          : item
      ));
      setQcWalkthroughs((previous) => ({
        ...previous,
        [walkthroughId]: {
          ...draft,
          steps: updatedSteps
        }
      }));
      stageQcChange(walkthroughId, qcChanges[walkthroughId]?.action || "save", updatedSteps, draft.title || walkthroughId, false);
      const generationMode = data.generation_mode ? ` (${data.generation_mode})` : "";
      setAdminMessage(`Generated a new image for step ${stepIndex + 1}${data.used_asset_sheet ? " using the asset sheet" : " using fallback generation"}${generationMode}. If it looks right, click Save All to keep it. ${data.image_url || ""}`);
    } catch (error) {
      console.error(error);
      setAdminMessage(error.name === "AbortError" ? "Image generation timed out after 4 minutes." : `Image generation failed: ${error.message}`);
    } finally {
      setQcImageGenerating((previous) => {
        const next = { ...previous };
        delete next[key];
        return next;
      });
    }
  }

  async function regenerateAllQcImages(walkthroughId) {
    const draft = qcWalkthroughs[walkthroughId];
    if (!draft?.steps?.length) {
      setAdminMessage("Open a walkthrough with steps before regenerating images.");
      return;
    }

    const token = getAdminToken("regenerate all images for this walkthrough");
    if (!token) {
      setAdminMessage("Image regeneration cancelled. No admin token was entered.");
      return;
    }

    setQcAllImagesGenerating((previous) => ({ ...previous, [walkthroughId]: true }));
    setAdminMessage(`Regenerating all images for ${draft.title || walkthroughId}...`);

    try {
      const response = await fetch(`${API_URL}/admin/qc/regenerate-all-images`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Token": token
        },
        body: JSON.stringify({
          walkthrough_id: walkthroughId,
          title: draft.title || "",
          query: draft.query || "",
          steps: draft.steps || [],
          visual_template: draft.visual_template || "",
          visual_assets: draft.visual_assets || {}
        })
      });
      const data = await response.json();

      if (!response.ok) {
        if (response.status === 401) {
          clearAdminToken();
        }
        throw new Error(data.detail || data.error || "Image regeneration failed.");
      }

      const updatedSteps = data.steps || draft.steps || [];
      setQcWalkthroughs((previous) => ({
        ...previous,
        [walkthroughId]: {
          ...draft,
          steps: updatedSteps
        }
      }));
      stageQcChange(walkthroughId, qcChanges[walkthroughId]?.action || "save", updatedSteps, draft.title || walkthroughId, false);
      setAdminMessage(`Generated ${data.step_count || updatedSteps.length} image(s) for ${draft.title || walkthroughId}. Click Save All to keep them.`);
    } catch (error) {
      console.error(error);
      setAdminMessage(`Image regeneration failed: ${error.message}`);
    } finally {
      setQcAllImagesGenerating((previous) => {
        const next = { ...previous };
        delete next[walkthroughId];
        return next;
      });
    }
  }


  async function saveAllQcChanges() {
    const actions = Object.entries(qcChanges)
      .filter(([, change]) => change?.action)
      .map(([walkthroughId, change]) => ({
        walkthrough_id: walkthroughId,
        action: change.action,
        steps: change.steps || qcWalkthroughs[walkthroughId]?.steps || [],
        title: change.title ?? qcWalkthroughs[walkthroughId]?.title,
        query: change.query ?? qcWalkthroughs[walkthroughId]?.query,
        visual_template: change.visual_template ?? qcWalkthroughs[walkthroughId]?.visual_template ?? ""
      }));

    if (!actions.length) {
      setAdminMessage("No QC changes to save.");
      return;
    }

    const token = getAdminToken("save QC changes");
    if (!token) {
      setAdminMessage("QC save cancelled. No token was entered.");
      return;
    }

    setQcSaving(true);
    try {
      const response = await fetch(`${API_URL}/admin/qc/save-all`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Token": token
        },
        body: JSON.stringify({ actions })
      });
      const data = await response.json();

      if (!response.ok) {
        clearAdminToken();
        throw new Error(data.detail || data.error || "QC save failed.");
      }

      setQcChanges({});
      setQcWalkthroughs({});
      setQcExpandedId("");
      const deletedCount = (data.results || []).filter((item) => item.status === "deleted").length;
      const mergedCount = (data.results || []).filter((item) => item.status === "merged_duplicate").length;
      setAdminMessage(`QC saved: ${data.processed_count || 0} item(s) updated. Merged duplicates: ${mergedCount}. Deleted: ${deletedCount}.`);
      loadAdminWalkthroughs();
      loadBuildStatus();
    } catch (error) {
      console.error(error);
      setAdminMessage(`QC save failed: ${error.message}`);
    } finally {
      setQcSaving(false);
    }
  }


  async function deleteQcWalkthroughNow(walkthroughId, title = "") {
    const token = getAdminToken("delete walkthroughs");
    if (!token) {
      setAdminMessage("Delete cancelled. No admin token was entered.");
      return;
    }

    setQcSaving(true);
    try {
      const response = await fetch(`${API_URL}/admin/qc/save-all`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Token": token
        },
        body: JSON.stringify({
          actions: [{
            walkthrough_id: walkthroughId,
            action: "delete",
            steps: []
          }]
        })
      });
      const data = await response.json();

      if (!response.ok) {
        clearAdminToken();
        throw new Error(data.detail || data.error || "Delete failed.");
      }

      const result = (data.results || [])[0] || {};
      const deleted = result.status === "deleted";

      if (!deleted) {
        throw new Error(result.message || `Walkthrough was not deleted. Status: ${result.status || "unknown"}.`);
      }

      setWalkthroughList((previous) => previous.filter((item) => {
        const itemId = qcItemId(item);
        return itemId !== walkthroughId && item.walkthrough_id !== walkthroughId;
      }));
      setQcChanges((previous) => {
        const next = { ...previous };
        delete next[walkthroughId];
        return next;
      });
      setQcWalkthroughs((previous) => {
        const next = { ...previous };
        delete next[walkthroughId];
        return next;
      });
      if (qcExpandedId === walkthroughId) {
        setQcExpandedId("");
      }
      setAdminMessage(`Deleted ${title || walkthroughId}.`);
      loadAdminWalkthroughs();
      loadBuildStatus();
    } catch (error) {
      console.error(error);
      setAdminMessage(`Delete failed: ${error.message}`);
    } finally {
      setQcSaving(false);
    }
  }


  async function markAllWalkthroughsAsDrafts() {
    const token = getAdminToken("mark all current walkthroughs as DRAFT");
    if (!token) {
      setAdminMessage("Draft migration cancelled. No token was entered.");
      return;
    }

    setQcSaving(true);
    try {
      const response = await fetch(`${API_URL}/admin/qc/mark-all-drafts`, {
        method: "POST",
        headers: {
          "X-Admin-Token": token
        }
      });
      const data = await response.json();

      if (!response.ok) {
        clearAdminToken();
        throw new Error(data.detail || data.error || "Draft migration failed.");
      }

      setAdminMessage(`Marked ${data.updated_count || 0} walkthrough(s) as DRAFT. Skipped ${data.skipped_count || 0}.`);
      loadAdminWalkthroughs();
      loadBuildStatus();
    } catch (error) {
      console.error(error);
      setAdminMessage(`Draft migration failed: ${error.message}`);
    } finally {
      setQcSaving(false);
    }
  }


  async function loadVisualMigrationReport(tokenOverride = "") {
    const token = tokenOverride || getAdminToken("load the visual migration report");
    if (!token) {
      setAdminMessage("Visual migration report cancelled. Enter the admin token above first.");
      return;
    }

    setVisualMigrationLoading(true);
    try {
      const response = await fetch(`${API_URL}/admin/qc/visual-migration-report?limit=10000&review_status=all`, {
        headers: {
          "X-Admin-Token": token
        },
        cache: "no-store"
      });
      const data = await response.json();

      if (!response.ok) {
        if (response.status === 401) {
          clearAdminToken();
        }
        throw new Error(data.detail || data.error || "Visual migration report failed.");
      }

      setVisualMigrationReport(data);
      const summary = data.summary || {};
      setAdminMessage(
        `Visual migration report: ${summary.walkthrough_count || 0} walkthrough(s), ${summary.missing_visual_template_count || 0} missing templates, ${summary.missing_asset_sheet_count || 0} missing asset sheets.`
      );
    } catch (error) {
      console.error(error);
      setAdminMessage(`Visual migration report failed: ${error.message}`);
    } finally {
      setVisualMigrationLoading(false);
    }
  }


  async function prepareVisualMigration({ generateAssetSheets = false, limit = 5 } = {}) {
    const token = getAdminToken(generateAssetSheets ? "generate visual asset sheets" : "prepare visual templates");
    if (!token) {
      setAdminMessage("Visual migration cancelled. No admin token was entered.");
      return;
    }

    if (generateAssetSheets) {
      const ok = window.confirm(
        `Generate up to ${limit} visual asset sheet image(s)? This uses paid image generation and can take several minutes.`
      );
      if (!ok) return;
    }

    setVisualMigrationLoading(true);
    setAdminMessage(
      generateAssetSheets
        ? `Generating up to ${limit} visual asset sheet(s)...`
        : `Preparing visual templates for up to ${limit} walkthrough(s)...`
    );

    try {
      const response = await fetch(`${API_URL}/admin/qc/prepare-visual-migration`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Token": token
        },
        cache: "no-store",
        body: JSON.stringify({
          limit,
          review_status: "all",
          dry_run: false,
          generate_asset_sheets: generateAssetSheets
        })
      });
      const data = await response.json();

      if (!response.ok) {
        if (response.status === 401) {
          clearAdminToken();
        }
        throw new Error(data.detail || data.error || "Visual migration preparation failed.");
      }

      setAdminMessage(
        generateAssetSheets
          ? `Generated ${data.generated_asset_sheet_count || 0} asset sheet(s). Prepared ${data.processed_count || 0} walkthrough(s).`
          : `Prepared visual templates for ${data.processed_count || 0} walkthrough(s).`
      );
      await loadVisualMigrationReport(token);
      loadAdminWalkthroughs();
    } catch (error) {
      console.error(error);
      setAdminMessage(`Visual migration failed: ${error.message}`);
    } finally {
      setVisualMigrationLoading(false);
    }
  }


  async function regenerateStepImage(stepId) {
    if (!selectedAdminWalkthrough) {
      return;
    }

    setAdminLoading(true);

    try {
      const response = await fetch(`${API_URL}/admin/regenerate-step-image`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          walkthrough_id: selectedAdminWalkthrough.walkthrough_id,
          step_id: stepId,
          correction: repairCorrectionRefs.current[stepId] ?? repairCorrections[stepId] ?? ""
        })
      });

      const data = await response.json();

      if (data.walkthrough) {
        setSelectedAdminWalkthrough(data.walkthrough);
        repairCorrectionRefs.current = {};
        setRepairCorrections({});
        setEditorDraft(JSON.parse(JSON.stringify(data.walkthrough)));
        setEditorDirty(false);
      }

      setAdminMessage(data.status === "pending_review" ? "New image generated for review." : `Image regeneration: ${data.status}`);
    } catch (error) {
      console.error(error);
      setAdminMessage("Could not regenerate image.");
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
        repairCorrectionRefs.current = {};
        setRepairCorrections({});
        setEditorDraft(JSON.parse(JSON.stringify(data.walkthrough)));
        setEditorDirty(false);
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
        repairCorrectionRefs.current = {};
        setRepairCorrections({});
        setEditorDraft(JSON.parse(JSON.stringify(data.walkthrough)));
        setEditorDirty(false);
      }

      setAdminMessage(`Image ${data.status}.`);
    } catch (error) {
      console.error(error);
      setAdminMessage("Could not revert image.");
    } finally {
      setAdminLoading(false);
    }
  }


  function toggleAdminPanel(panelId) {
    setAdminPanels((previous) => ({
      ...previous,
      [panelId]: !previous[panelId]
    }));
  }


  function updateEditorField(field, value) {
    setEditorDraft((previous) => {
      if (!previous) {
        return previous;
      }
      return {
        ...previous,
        [field]: value
      };
    });
    setEditorDirty(true);
  }


  function updateEditorStep(stepId, field, value) {
    setEditorDraft((previous) => {
      if (!previous) {
        return previous;
      }
      return {
        ...previous,
        steps: (previous.steps || []).map((step) => (
          Number(step.id) === Number(stepId)
            ? { ...step, [field]: value }
            : step
        ))
      };
    });
    setEditorDirty(true);
  }


  function moveEditorStep(stepId, direction) {
    if (!editorDraft?.steps?.length) {
      return;
    }

    const steps = [...editorDraft.steps];
    const index = steps.findIndex((step) => Number(step.id) === Number(stepId));
    const newIndex = index + direction;

    if (index < 0 || newIndex < 0 || newIndex >= steps.length) {
      return;
    }

    const [removed] = steps.splice(index, 1);
    steps.splice(newIndex, 0, removed);

    const renumbered = steps.map((step, idx) => ({
      ...step,
      id: idx + 1
    }));

    setEditorDraft({
      ...editorDraft,
      steps: renumbered
    });
    setEditorDirty(true);
  }


  async function saveEditorWalkthrough() {
    if (!editorDraft) {
      return;
    }

    const token = getAdminToken("save edited walkthroughs");
    if (!token) {
      setAdminMessage("Save cancelled. No admin token was entered.");
      return;
    }

    setEditorSaving(true);
    setAdminMessage("Saving walkthrough...");

    try {
      const response = await fetch(`${API_URL}/admin/save-walkthrough`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Token": token
        },
        body: JSON.stringify({
          walkthrough: editorDraft
        })
      });

      const data = await response.json();

      if (!response.ok || data.status === "error") {
        if (response.status === 401) {
          clearAdminToken();
        }
        throw new Error(data.error || data.detail || "Save failed.");
      }

      setSelectedAdminWalkthrough(data.walkthrough || editorDraft);
      setEditorDraft(JSON.parse(JSON.stringify(data.walkthrough || editorDraft)));
      setEditorDirty(false);
      setAdminMessage("✓ Walkthrough saved.");
      loadAdminWalkthroughs();
    } catch (error) {
      console.error(error);
      setAdminMessage(`Save failed: ${error.message}`);
    } finally {
      setEditorSaving(false);
    }
  }


  function previewEditorWalkthrough() {
    if (!editorDraft) {
      return;
    }

    setWalkthrough(editorDraft);
    setStepIndex(0);
    setComplete(false);
    setStarted(true);
    setClarifying(false);
    setScreen("walkthrough");
  }


  async function runQueueLimit(limit) {
    setAdminLoading(true);
    setAdminMessage(`Running ${limit === 999 ? "all available" : limit} queued job(s)...`);

    try {
      const response = await fetch(`${API_URL}/admin/process-bulk-queries?limit=${limit}`, {
        method: "POST",
        cache: "no-store"
      });
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.error || "Queue run failed.");
      }

      setAdminMessage(`Run complete: processed ${data.processed_count || 0}, failed ${data.failed_count || 0}, remaining ${data.remaining_queued || 0}.`);
      loadBulkJobList();
      loadAdminStatus();
      loadBuildStatus();
    } catch (error) {
      console.error(error);
      setAdminMessage(`Run failed: ${error.message}`);
    } finally {
      setAdminLoading(false);
    }
  }


  function AdminSection({ panelId, title, children, actions }) {
    const isOpen = !!adminPanels[panelId];

    return (
      <section className="adminCard">
        <div className="adminCardHeader">
          <button
            className="secondaryButton"
            style={{ padding: "8px 12px", minWidth: "42px" }}
            onClick={() => toggleAdminPanel(panelId)}
            aria-label={isOpen ? `Collapse ${title}` : `Expand ${title}`}
          >
            {isOpen ? "▾" : "▸"}
          </button>
          <h2 style={{ flex: 1 }}>{title}</h2>
          {actions}
        </div>
        {isOpen && children}
      </section>
    );
  }



  useEffect(() => {
    logVisitorEvent("session_start", {
      metadata: {
        initial_path: window.location.pathname
      }
    });

    const handlePageHide = () => {
      logVisitorEvent("session_end", {
        time_spent_seconds: Math.round((Date.now() - sessionStartedAtRef.current) / 1000),
        metadata: {
          final_screen: screen
        }
      });
    };

    window.addEventListener("pagehide", handlePageHide);
    return () => window.removeEventListener("pagehide", handlePageHide);
  }, []);


  useEffect(() => {
    if (!visitorLog) {
      return;
    }

    const cachedToken = window.localStorage.getItem(ADMIN_TOKEN_STORAGE_KEY);
    if (cachedToken) {
      loadVisitors(cachedToken);
    }
  }, [visitorStartDate, visitorEndDate]);


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
      <style>{`
        @keyframes rsSpin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
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

          <div className="adminTokenBar">
            <label>
              <span>Admin token</span>
              <input
                type="password"
                value={adminTokenValue}
                onChange={(event) => {
                  setAdminTokenValue(event.target.value);
                  setAdminTokenStatus("Unsaved");
                }}
                placeholder="Paste token for protected admin actions"
              />
            </label>
            <button className="secondaryButton" onClick={saveAdminToken}>
              Save Token
            </button>
            <button className="secondaryButton" onClick={clearAdminToken}>
              Clear
            </button>
            <span className={`adminTokenStatus ${adminTokenStatus === "Saved" ? "saved" : ""}`}>
              {adminTokenStatus}
            </span>
          </div>

          <AdminSection
            panelId="qc"
            title="Step Order Quality Control"
            actions={
              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
                <select className="selectBox compact" value={qcFilter} onChange={(event) => setQcFilter(event.target.value)}>
                  <option value="draft">DRAFT</option>
                  <option value="approved">APPROVED</option>
                </select>
                <button className="secondaryButton" onClick={loadAdminWalkthroughs} disabled={adminLoading}>
                  Refresh
                </button>
                <button className="secondaryButton" onClick={markAllWalkthroughsAsDrafts} disabled={qcSaving}>
                  Mark Existing as Drafts
                </button>
                <button className="startButton" onClick={saveAllQcChanges} disabled={qcSaving || !Object.keys(qcChanges).length}>
                  {qcSaving ? "Saving..." : `Save All (${Object.keys(qcChanges).length})`}
                </button>
              </div>
            }
          >
            <div className="qcWorkspace">
              <div className="qcToolbar">
                <div>
                  <strong>{qcFilter === "approved" ? "Approved walkthroughs" : "Draft walkthroughs"}</strong>
                  <span>{qcListItems().length} item(s)</span>
                </div>
                <p className="adminHelp">
                  Delete draft rows directly from the list, or expand a draft to adjust step order and stage approval.
                </p>
              </div>

              <div className="qcList">
                {qcListItems().map((item) => {
                  const walkthroughId = qcItemId(item);
                  const expanded = qcExpandedId === walkthroughId;
                  const draft = qcWalkthroughs[walkthroughId];
                  const staged = qcChanges[walkthroughId]?.action || "";
                  const status = reviewStatusFor(item);
                  const stagedLabel = staged === "approve"
                    ? "Approval staged"
                    : staged === "save"
                      ? "Save staged"
                      : staged === "delete"
                        ? "Delete staged"
                        : "";

                  return (
                    <div key={`qc-${walkthroughId}`} className={`qcRow ${expanded ? "qcRowOpen" : ""}`}>
                      <div className="qcRowSummary">
                        <button className="qcRowExpand" onClick={() => toggleQcWalkthrough(walkthroughId)}>
                          <span className="qcCaret">{expanded ? "▾" : "▸"}</span>
                          <span className="qcTitle">{displayText(item.title, 120)}</span>
                        </button>
                        <span className={`qcBadge qcBadge-${staged || status}`}>{staged || status}</span>
                        <span className="qcMeta">{item.step_count} steps</span>
                        {status !== "approved" && (
                          <button
                            className="qcDeleteButton"
                            onClick={() => deleteQcWalkthroughNow(walkthroughId, item.title)}
                            disabled={qcSaving}
                            title="Delete this walkthrough"
                          >
                            {qcSaving ? "Deleting" : "Delete"}
                          </button>
                        )}
                      </div>

                      {expanded && (
                        <div className="qcExpanded">
                          {draft ? (
                            <>
                              <div className="qcExpandedHeader">
                                <div>
                                  <strong>{draft.title || draft.query || draft.walkthrough_id}</strong>
                                  <span>{draft.query ? `Query: ${draft.query}` : "Query not set yet"}</span>
                                  <span>{draft.quality_status || "unvalidated"} · storage id: {draft.walkthrough_id}</span>
                                </div>
                                <div className="qcActions">
                                  {status !== "approved" && (
                                    <button
                                      className="secondaryButton"
                                      onClick={() => adoptApprovedMatch(walkthroughId)}
                                      disabled={qcSaving}
                                    >
                                      Use Approved Match
                                    </button>
                                  )}
                                  <button
                                    className="secondaryButton"
                                    onClick={() => regenerateAllQcImages(walkthroughId)}
                                    disabled={!!qcAllImagesGenerating[walkthroughId]}
                                  >
                                    {qcAllImagesGenerating[walkthroughId] ? "Regenerating Images..." : "Regenerate All Images"}
                                  </button>
                                  <button
                                    className="secondaryButton"
                                    onClick={() => stageQcChange(walkthroughId, "save", draft.steps || [], item.title)}
                                  >
                                    {staged === "save" ? "Save Staged" : "Stage Save"}
                                  </button>
                                  <button
                                    className="doneButton"
                                    onClick={() => stageQcChange(walkthroughId, "approve", draft.steps || [], item.title)}
                                  >
                                    {staged === "approve" ? "Approval Staged" : "Stage Approve"}
                                  </button>
                                  {status !== "approved" && (
                                    <button
                                      className="secondaryButton dangerButton"
                                      onClick={() => stageQcChange(walkthroughId, "delete", draft.steps || [], item.title)}
                                    >
                                      {staged === "delete" ? "Delete Staged" : "Stage Delete"}
                                    </button>
                                  )}
                                </div>
                              </div>

                              <div className="qcMetadataEditor">
                                <label>
                                  <span>Title shown in admin</span>
                                  <QcDraftField
                                    className="qcStepInput"
                                    fieldKey={`${walkthroughId}-title`}
                                    value={draft.title || ""}
                                    onCommit={(value) => updateQcMetadata(walkthroughId, "title", value)}
                                    placeholder="Clear walkthrough title"
                                  />
                                </label>
                                <label>
                                  <span>Query this walkthrough should answer</span>
                                  <QcDraftField
                                    className="qcStepInput"
                                    fieldKey={`${walkthroughId}-query`}
                                    value={draft.query || ""}
                                    onCommit={(value) => updateQcMetadata(walkthroughId, "query", value)}
                                    placeholder="Example: install a refrigerator icemaker water line"
                                  />
                                </label>
                                <label className="qcVisualTemplateField">
                                  <span>Visual template for consistent images</span>
                                  <QcDraftField
                                    as="textarea"
                                    className="qcStepTextarea"
                                    fieldKey={`${walkthroughId}-visual-template`}
                                    value={draft.visual_template || ""}
                                    onCommit={(value) => updateQcMetadata(walkthroughId, "visual_template", value)}
                                    placeholder="Example: same white drop-in bathroom sink set into a beige laminate countertop, chrome two-handle faucet, white vanity cabinet, same worker in tan shirt and gloves."
                                  />
                                </label>
                                {draft.visual_assets && (
                                  <div className="qcVisualAssetsPanel">
                                    <div>
                                      <span>Visual asset sheet</span>
                                      <strong>{draft.visual_assets.asset_status || "ready"}</strong>
                                      <p>{draft.visual_assets.primary_object || draft.visual_assets.locked_prompt || "No primary asset description yet."}</p>
                                      {draft.visual_assets.product && <p>{draft.visual_assets.product}</p>}
                                    </div>
                                    {draft.visual_assets.asset_sheet_url && (
                                      <img
                                        src={apiAssetUrl(draft.visual_assets.asset_sheet_url)}
                                        alt="Walkthrough visual asset sheet"
                                      />
                                    )}
                                  </div>
                                )}
                              </div>

                              {stagedLabel && (
                                <div className="qcNotice qcNoticeStaged">
                                  <strong>{stagedLabel}.</strong>
                                  <span>Click Save All to apply this change to persistent storage.</span>
                                  <button className="startButton compactButton" onClick={saveAllQcChanges} disabled={qcSaving}>
                                    {qcSaving ? "Saving..." : `Save All (${Object.keys(qcChanges).length})`}
                                  </button>
                                </div>
                              )}

                              {draft.step_sequence_validation?.issues?.length ? (
                                <div className="qcNotice">
                                  {draft.step_sequence_validation.issues.map((issue, index) => (
                                    <div key={`qc-issue-${walkthroughId}-${index}`}>{issue.message || issue.type}</div>
                                  ))}
                                </div>
                              ) : null}

                              <div className="qcStepList">
                                {(draft.steps || []).map((step, index) => {
                                  const imageDirectionKey = qcImageDirectionCacheKey(walkthroughId, index);
                                  const imageDirectionValue = qcDraftValueCache.has(imageDirectionKey)
                                    ? qcDraftValueCache.get(imageDirectionKey)
                                    : step.imageDirection || "";

                                  return (
                                  <div key={`qc-step-${walkthroughId}-${index}`} className="qcStep">
                                    <div className="qcStepNumber">{index + 1}</div>
                                    <div className="qcStepEditor">
                                      <QcDraftField
                                        className="qcStepInput"
                                        fieldKey={`${walkthroughId}-${index}-imageLabel`}
                                        value={step.imageLabel || ""}
                                        onCommit={(value) => updateQcStep(walkthroughId, index, "imageLabel", value)}
                                        placeholder="Step label"
                                      />
                                      <QcDraftField
                                        className="qcStepInput"
                                        fieldKey={`${walkthroughId}-${index}-instruction`}
                                        value={step.instruction || ""}
                                        onCommit={(value) => updateQcStep(walkthroughId, index, "instruction", value)}
                                        placeholder="Instruction"
                                      />
                                      <QcDraftField
                                        as="textarea"
                                        className="qcStepTextarea"
                                        fieldKey={`${walkthroughId}-${index}-detail`}
                                        value={step.detail || ""}
                                        onCommit={(value) => updateQcStep(walkthroughId, index, "detail", value)}
                                        placeholder="Step detail"
                                      />
                                      <button
                                        type="button"
                                        className={`qcImageDirectionButton ${imageDirectionValue ? "hasDirection" : ""}`}
                                        onClick={() => openImageDirectionEditor(walkthroughId, index)}
                                      >
                                        <strong>{imageDirectionValue ? "Edit image direction" : "Add image direction"}</strong>
                                        <span>{imageDirectionValue || IMAGE_DIRECTION_PLACEHOLDER}</span>
                                      </button>
                                      {step.imageUrl && (
                                        <img className="qcStepImagePreview" src={apiAssetUrl(step.imageUrl)} alt={step.imageLabel || `Step ${step.id}`} />
                                      )}
                                    </div>
                                    <div className="qcStepActions">
                                      <button
                                        className={step.imageStale ? "startButton compactButton" : "secondaryButton"}
                                        onMouseDown={(event) => event.preventDefault()}
                                        onClick={() => generateQcStepImage(walkthroughId, index)}
                                        disabled={!!qcImageGenerating[`${walkthroughId}-${index}`] || !!qcAllImagesGenerating[walkthroughId]}
                                      >
                                        {qcImageGenerating[`${walkthroughId}-${index}`] ? "Generating..." : "Generate New Image"}
                                      </button>
                                      <button className="secondaryButton" onClick={() => moveQcStep(walkthroughId, index, -1)} disabled={index === 0}>↑</button>
                                      <button className="secondaryButton" onClick={() => moveQcStep(walkthroughId, index, 1)} disabled={index === (draft.steps || []).length - 1}>↓</button>
                                      <button className="secondaryButton" onClick={() => addQcStepAfter(walkthroughId, index)}>+ Step</button>
                                      <button className="secondaryButton dangerButton" onClick={() => deleteQcStep(walkthroughId, index)} disabled={(draft.steps || []).length <= 1}>Delete</button>
                                    </div>
                                  </div>
                                  );
                                })}
                                <button className="secondaryButton qcAddStepButton" onClick={() => addQcStepAfter(walkthroughId)}>
                                  + Add Step At End
                                </button>
                              </div>
                            </>
                          ) : (
                            <p className="adminHelp">Loading walkthrough...</p>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </AdminSection>

          <AdminSection
            panelId="visualMigration"
            title="Visual Consistency Migration"
            actions={
              <div className="adminActionRow">
                <button className="secondaryButton" onClick={() => preserveScrollAfter(loadVisualMigrationReport)} disabled={visualMigrationLoading}>
                  {visualMigrationLoading ? "Working..." : "Load Report"}
                </button>
                <button className="secondaryButton" onClick={() => preserveScrollAfter(() => prepareVisualMigration({ limit: 10 }))} disabled={visualMigrationLoading}>
                  Prepare Missing Templates
                </button>
                <button className="secondaryButton" onClick={() => preserveScrollAfter(() => prepareVisualMigration({ generateAssetSheets: true, limit: 3 }))} disabled={visualMigrationLoading}>
                  Generate 3 Asset Sheets
                </button>
              </div>
            }
          >
            <div className="libraryWorkspace">
              <p className="adminHelp">
                Start here before regenerating old walkthrough images. This locks a visual template and asset metadata first, then lets you generate asset sheets in small paid batches.
              </p>
              {visualMigrationReport?.summary ? (
                <>
                  <div className="libraryStats">
                    <span>{visualMigrationReport.summary.walkthrough_count || 0} walkthroughs</span>
                    <span>{visualMigrationReport.summary.missing_visual_template_count || 0} missing templates</span>
                    <span>{visualMigrationReport.summary.missing_asset_sheet_count || 0} missing asset sheets</span>
                    <span>{visualMigrationReport.summary.full_regen_image_calls || 0} full-regeneration image calls</span>
                    <span>
                      Est. medium full pass: ${visualMigrationReport.summary.estimated_full_regen_costs?.medium ?? 0}
                    </span>
                  </div>
                  <div className="visualMigrationList">
                    {(visualMigrationReport.items || []).slice(0, 12).map((item) => (
                      <div key={`visual-migration-${item.walkthrough_id}`} className="visualMigrationItem">
                        <div className="visualMigrationMain">
                          <strong>{displayText(item.title, 120)}</strong>
                          <span>{item.category} · {item.step_count} steps · {item.readiness.replaceAll("_", " ")}</span>
                        </div>
                        <div className="visualMigrationMeta">
                          <span>{item.has_visual_template ? "Template ready" : "Needs template"}</span>
                          <span>{item.has_asset_sheet ? "Asset sheet ready" : "Needs asset sheet"}</span>
                          <span>${item.estimated_full_regen_costs?.medium ?? 0} med.</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <p className="adminHelp">Load the report to see the migration queue and estimated image-generation cost.</p>
              )}
            </div>
          </AdminSection>

          <AdminSection
            panelId="library"
            title="Walkthrough Library"
            actions={
              <div className="adminActionRow">
                <button className="secondaryButton" onClick={() => loadWalkthroughLibrary()} disabled={libraryLoading || libraryRebuilding}>
                  {libraryLoading ? "Refreshing..." : "Refresh Library"}
                </button>
                <button className="secondaryButton" onClick={() => rebuildWalkthroughIndex()} disabled={libraryLoading || libraryRebuilding}>
                  {libraryRebuilding ? "Rebuilding..." : "Rebuild Index"}
                </button>
              </div>
            }
          >
            <div className="libraryWorkspace">
              {libraryMessage && (
                <div className={`libraryNotice ${libraryMessage.toLowerCase().includes("failed") ? "error" : ""}`}>
                  {libraryMessage}
                </div>
              )}

              <div className="libraryStats">
                <div><strong>{walkthroughLibrary?.summary?.stored_walkthrough_count || 0}</strong><span>Stored</span></div>
                <div><strong>{walkthroughLibrary?.summary?.taxonomy_entries_with_existing_walkthroughs || 0}</strong><span>Matched</span></div>
                <div><strong>{walkthroughLibrary?.summary?.unmatched_existing_walkthrough_count || 0}</strong><span>Unmatched</span></div>
                <div><strong>{walkthroughLibrary?.summary?.prospective_taxonomy_entries_without_existing_walkthroughs || 0}</strong><span>Prospective</span></div>
              </div>

              <div className="libraryControls">
                <div className="segmentedControl">
                  <button className={libraryView === "stored" ? "active" : ""} onClick={() => setLibraryView("stored")}>
                    Stored
                  </button>
                  <button className={libraryView === "prospective" ? "active" : ""} onClick={() => setLibraryView("prospective")}>
                    Prospective
                  </button>
                </div>
                <select className="selectBox compact" value={libraryFilter} onChange={(event) => setLibraryFilter(event.target.value)}>
                  <option value="all">All</option>
                  <option value="draft">Draft</option>
                  <option value="matched">Matched</option>
                  <option value="unmatched">Unmatched</option>
                  <option value="branch">Branch Needed</option>
                </select>
                <input
                  className="queryBox librarySearch"
                  type="search"
                  value={librarySearch}
                  onChange={(event) => setLibrarySearch(event.target.value)}
                  placeholder="Search title, query, alias, category"
                />
              </div>

              <div className="libraryList">
                {libraryView === "stored" ? (
                  libraryStoredItems().map((item) => (
                    <div key={`library-${item.walkthrough_id}`} className="libraryRow">
                      <div className="libraryMain">
                        <strong>{displayText(item.title, 95)}</strong>
                        <span>{displayText(item.canonical_query || item.walkthrough_id, 110)}</span>
                      </div>
                      <span className={`qcBadge qcBadge-${item.review_status || "draft"}`}>{item.review_status || "draft"}</span>
                      <span className={`libraryMatch ${item.coverage_status === "matched_taxonomy" ? "matched" : "unmatched"}`}>
                        {item.coverage_status === "matched_taxonomy" ? `Matched ${Math.round((item.taxonomy_match_score || 0) * 100)}%` : "Unmatched"}
                      </span>
                      <span className="libraryMeta">{item.category || "generic"}</span>
                      <span className="libraryMeta">{item.step_count || 0} steps</span>
                      <button
                        className="secondaryButton compactButton"
                        onClick={() => loadAdminWalkthrough(item.storage_walkthrough_id || item.walkthrough_id)}
                        disabled={adminLoading}
                      >
                        Repair
                      </button>
                    </div>
                  ))
                ) : (
                  libraryProspectiveItems().map((item) => (
                    <div key={`prospective-${item.taxonomy_walkthrough_id}`} className="libraryRow prospectiveRow">
                      <div className="libraryMain">
                        <strong>{displayText(item.title, 95)}</strong>
                        <span>{displayText(item.canonical_query || item.taxonomy_walkthrough_id, 110)}</span>
                      </div>
                      <span className="libraryMatch unmatched">Needed</span>
                      <span className="libraryMeta">{item.category || "generic"}</span>
                      <span className="libraryMeta">{item.alias_count || 0} aliases</span>
                      <span className="libraryMeta">{item.requires_branch_selection ? "branch" : item.safety_level || "standard"}</span>
                    </div>
                  ))
                )}
              </div>

              {walkthroughLibrary && (libraryView === "stored" ? libraryStoredItems().length : libraryProspectiveItems().length) === 0 && (
                <p className="adminHelp">No library items match the current filters.</p>
              )}
              {!walkthroughLibrary && (
                <p className="adminHelp">Load the library to see stored walkthroughs, taxonomy matches, unmatched drafts, and prospective walkthroughs.</p>
              )}
            </div>
          </AdminSection>

          <AdminSection
            panelId="visitors"
            title="VISITORS"
            actions={
              <div className="adminActionRow">
                <button className="secondaryButton" onClick={() => loadVisitors()} disabled={visitorLoading}>
                  {visitorLoading ? "Loading..." : "Refresh Visitors"}
                </button>
                <button className="startButton" onClick={exportVisitorsCsv} disabled={visitorLoading}>
                  Export CSV
                </button>
              </div>
            }
          >
            <div className="visitorWorkspace">
              <div className="visitorControls">
                <label>
                  <span>Start date</span>
                  <input type="date" value={visitorStartDate} onChange={(event) => setVisitorStartDate(event.target.value)} />
                </label>
                <label>
                  <span>End date</span>
                  <input type="date" value={visitorEndDate} onChange={(event) => setVisitorEndDate(event.target.value)} />
                </label>
                <button className="secondaryButton" onClick={() => { setVisitorStartDate(""); setVisitorEndDate(todayDateInputValue()); }}>
                  Reset Dates
                </button>
              </div>

              <div className="visitorStats">
                <div><strong>{visitorLog?.summary?.event_count || 0}</strong><span>Events</span></div>
                <div><strong>{visitorLog?.summary?.walkthrough_event_count || 0}</strong><span>Query events</span></div>
                <div><strong>{visitorLog?.summary?.unique_ip_count || 0}</strong><span>Unique IPs</span></div>
                <div><strong>{formatDuration(visitorLog?.summary?.total_time_spent_seconds || 0)}</strong><span>Total time</span></div>
              </div>

              <div className="visitorList">
                {(visitorLog?.visitors || []).map((event, index) => (
                  <div className="visitorRow" key={`visitor-${event.timestamp}-${index}`}>
                    <span className="visitorDate">{formatVisitorDate(event.timestamp)}</span>
                    <span className="visitorEvent">{event.event || "event"}</span>
                    <span className="visitorQuery">{displayText(event.query || event.walkthrough_id || event.path || "No query", 110)}</span>
                    <span className="visitorDuration">{formatDuration(event.time_spent_seconds)}</span>
                    <span className="visitorIp">{event.ip_address || "IP unavailable"}</span>
                  </div>
                ))}
              </div>

              {visitorLog && !(visitorLog.visitors || []).length && (
                <p className="adminHelp">No visitor events match this date range yet.</p>
              )}
              {!visitorLog && (
                <p className="adminHelp">Click Refresh Visitors to load usage events, queries, time spent, IP addresses when available, and timestamps.</p>
              )}
            </div>
          </AdminSection>

          <AdminSection
            panelId="catalog"
            title="Catalog Intelligence v2"
            actions={
              <button className="secondaryButton" onClick={loadCatalogPipelineStatus} disabled={adminLoading || !!catalogPipelineRunning}>
                Refresh Catalog
              </button>
            }
          >
            <p className="adminHelp">
              Build reusable product packages from manufacturer product pages. Product packages stay separate from walkthroughs and can be reused by compatible walkthrough families.
            </p>

            <div style={{ border: "1px solid rgba(0,0,0,0.14)", borderRadius: "18px", padding: "14px", marginBottom: "16px", background: "#f8fafc" }}>
              <h3 style={{ margin: "0 0 8px" }}>Build Product Package</h3>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "10px" }}>
                <label className="fieldLabel">Category<input value={productPackageCategory} onChange={(event) => setProductPackageCategory(event.target.value)} placeholder="toilet" /></label>
                <label className="fieldLabel">Brand<input value={productPackageBrand} onChange={(event) => setProductPackageBrand(event.target.value)} placeholder="Niagara" /></label>
                <label className="fieldLabel">Model<input value={productPackageModel} onChange={(event) => setProductPackageModel(event.target.value)} placeholder="Original Stealth" /></label>
              </div>
              <label className="fieldLabel" style={{ marginTop: "10px" }}>Manufacturer product page URL<input value={productPackageUrl} onChange={(event) => setProductPackageUrl(event.target.value)} placeholder="https://manufacturer.com/product-page" /></label>
              <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap", marginTop: "12px" }}>
                <button className="startButton" onClick={buildProductPagePackage} disabled={productPackageRunning || !productPackageBrand.trim() || !productPackageModel.trim() || !productPackageUrl.trim()}>
                  {productPackageRunning ? "Building Package..." : "Build Product Package"}
                </button>
                <button className="secondaryButton" onClick={testBuildNiagaraStealth} disabled={productPackageRunning}>
                  Test Build Niagara Stealth
                </button>
              </div>
            </div>

            {catalogPipelineStatus?.items?.length ? (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "10px" }}>
                {catalogPipelineStatus.items.map((item) => {
                  const key = catalogItemKey(item);
                  const diagnostic = photoDiagnostics[key];
                  const diagnosticPhotoUrl = diagnostic?.cached_photo_url || diagnostic?.photo?.local_url || "";
                  const photoUrl = item.photo?.local_url || diagnosticPhotoUrl;
                  const hasPhoto = Boolean(photoUrl);
                  const photoStatus = hasPhoto ? "cached" : (item.photo?.status || "unknown");
                  const candidateCount = Array.isArray(diagnostic?.image_candidates) ? diagnostic.image_candidates.length : null;

                  return (
                    <div key={`${item.brand}-${item.model}`} style={{ border: "1px solid rgba(0,0,0,0.12)", borderRadius: "14px", padding: "12px", background: "white" }}>
                      <strong>{item.brand} {item.model}</strong>
                      <div style={{ fontSize: "12px", marginTop: "6px" }}>
                        Photo: {photoStatus} · Manual: {item.manual?.status || "unknown"} · Overlay: {item.overlay?.status || "unknown"}
                      </div>
                      <div style={{ fontSize: "12px" }}>Confidence: <strong>{item.confidence || "UNKNOWN"}</strong></div>
                      <div style={{ fontSize: "12px", color: "#555" }}>Source: {item.source || "starter_catalog"}</div>

                      <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginTop: "8px" }}>
                        <button className="secondaryButton" onClick={() => runCatalogPipeline(item, "all")} disabled={!!catalogPipelineRunning || !!photoActionKey}>
                          {catalogPipelineRunning === `${item.brand}-${item.model}-all` ? "Running..." : "Run All"}
                        </button>
                        {hasPhoto && <a className="secondaryButton" href={apiAssetUrl(photoUrl)} target="_blank" rel="noreferrer">View Photo</a>}
                        {item.manual?.local_url && <a className="secondaryButton" href={apiAssetUrl(item.manual.local_url)} target="_blank" rel="noreferrer">View PDF</a>}
                        {item.photo?.product_page_url && <a className="secondaryButton" href={apiAssetUrl(item.photo.product_page_url)} target="_blank" rel="noreferrer">Product Page</a>}
                        <button className="secondaryButton" onClick={() => diagnoseProductPhoto(item)} disabled={!!catalogPipelineRunning || !!photoActionKey}>
                          {photoActionKey === `${key}-diagnose` ? "Loading Photos..." : (hasPhoto ? "Change Photo" : "Diagnose Photo")}
                        </button>
                      </div>

                      <div style={{ marginTop: "10px", display: "grid", gap: "6px" }}>
                        {hasPhoto && (
                          <div style={{ display: "flex", gap: "10px", alignItems: "center", padding: "8px", borderRadius: "12px", background: "#f8fafc" }}>
                            <img src={apiAssetUrl(photoUrl)} alt={`${item.brand} ${item.model}`} style={{ width: "64px", height: "64px", objectFit: "contain", background: "white", borderRadius: "8px", border: "1px solid rgba(0,0,0,0.08)" }} />
                            <div style={{ fontSize: "12px" }}>
                              <strong>Current cached photo</strong>
                              <div style={{ color: "#555" }}>Use Change Photo below to pick a better candidate or paste a manufacturer image URL.</div>
                            </div>
                          </div>
                        )}
                        <label className="fieldLabel">
                          Manufacturer image URL override
                          <input
                            value={photoOverrideUrls[key] || ""}
                            onChange={(event) => setPhotoOverrideUrls((current) => ({ ...current, [key]: event.target.value }))}
                            placeholder="Paste manufacturer-hosted image URL"
                          />
                        </label>
                        <button className="secondaryButton" onClick={() => cacheProductPhotoFromUrl(item)} disabled={!!catalogPipelineRunning || !!photoActionKey || !(photoOverrideUrls[key] || "").trim()}>
                          {photoActionKey === `${key}-cache` ? "Caching Photo..." : (hasPhoto ? "Replace with Pasted Photo" : "Cache Photo")}
                        </button>
                      </div>

                      {diagnostic && (
                        <div style={{ marginTop: "10px", padding: "10px", borderRadius: "12px", background: "#f8fafc", fontSize: "12px" }}>
                          <strong>Photo Diagnostics</strong>
                          <div>Image candidates: {candidateCount ?? 0}</div>
                          {diagnostic.rejected_count !== undefined && diagnostic.rejected_count > 0 && <div>Rejected candidates: {diagnostic.rejected_count}</div>}
                          <div>Download status: {diagnostic.download_status || "unknown"}</div>
                          {diagnostic.attempted_count !== undefined && <div>Download attempts: {diagnostic.attempted_count}</div>}
                          {diagnostic.selected_candidate && <div style={{ wordBreak: "break-all" }}>Cached candidate: {diagnostic.selected_candidate}</div>}
                          {!diagnostic.selected_candidate && diagnostic.best_candidate && <div style={{ wordBreak: "break-all" }}>Best candidate: {diagnostic.best_candidate}</div>}
                          {diagnostic.cached_photo_url && <div><a href={apiAssetUrl(diagnostic.cached_photo_url)} target="_blank" rel="noreferrer">View cached photo</a></div>}
                          {diagnostic.failure_reason && <div style={{ color: "#9b1c1c" }}>Reason: {diagnostic.failure_reason}</div>}

                          {Array.isArray(diagnostic.image_candidates) && diagnostic.image_candidates.length > 0 && (
                            <div style={{ marginTop: "10px" }}>
                              <strong>Choose Product Photo</strong>
                              <div style={{ color: "#555", margin: "3px 0 8px" }}>
                                Pick the clearest full-product manufacturer image. Avoid close-ups, lifestyle scenes, and similar-but-different products.
                              </div>
                              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginBottom: "8px" }}>
                                {hasPhoto && <a className="secondaryButton" href={apiAssetUrl(photoUrl)} target="_blank" rel="noreferrer">View Current Photo</a>}
                                <button className="secondaryButton" onClick={() => rejectProductPhotoCandidates(item)} disabled={!!catalogPipelineRunning || !!photoActionKey}>
                                  {photoActionKey === `${key}-reject` ? "Rejecting..." : "Reject All Found Photos"}
                                </button>
                              </div>
                              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(92px, 1fr))", gap: "8px", maxHeight: "310px", overflowY: "auto", paddingRight: "4px" }}>
                                {diagnostic.image_candidates.slice(0, 24).map((candidateUrl, candidateIndex) => (
                                  <div key={`${key}-candidate-${candidateIndex}`} style={{ border: "1px solid rgba(0,0,0,0.12)", borderRadius: "10px", padding: "6px", background: "white" }}>
                                    <a href={candidateUrl} target="_blank" rel="noreferrer" title={candidateUrl}>
                                      <img
                                        src={candidateUrl}
                                        alt={`Candidate ${candidateIndex + 1}`}
                                        loading="lazy"
                                        style={{ width: "100%", height: "78px", objectFit: "contain", background: "#f1f5f9", borderRadius: "8px" }}
                                        onError={(event) => { event.currentTarget.style.display = "none"; }}
                                      />
                                    </a>
                                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "4px", marginTop: "5px" }}>
                                      <span style={{ fontSize: "11px", color: "#666" }}>#{candidateIndex + 1}</span>
                                      <button
                                        className="secondaryButton"
                                        style={{ padding: "5px 7px", fontSize: "11px", borderRadius: "8px" }}
                                        onClick={() => cacheProductPhotoCandidate(item, candidateUrl)}
                                        disabled={!!catalogPipelineRunning || !!photoActionKey}
                                      >
                                        {photoActionKey === `${key}-select` ? "Saving..." : (hasPhoto ? "Replace" : "Use")}
                                      </button>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="adminHelp">Click Refresh Catalog to load available packages and starter models.</p>
            )}
          </AdminSection>

          <AdminSection panelId="status" title="System Status" actions={<button className="secondaryButton" onClick={loadAdminStatus} disabled={adminLoading}>Refresh</button>}>
            {adminStatus ? (
              <div className="adminStats">
                <div><strong>{adminStatus.bulk_query_count}</strong><span>Total queries</span></div>
                <div><strong>{adminStatus.bulk_completed_count || 0}</strong><span>Completed</span></div>
                <div><strong>{adminStatus.bulk_queued_count || 0}</strong><span>Queued</span></div>
                <div><strong>{adminStatus.bulk_failed_count || 0}</strong><span>Failed</span></div>
                <div><strong>{adminStatus.catalog_request_count}</strong><span>Catalog requests</span></div>
                <div><strong>{adminStatus.catalog_category_count}</strong><span>Catalog categories</span></div>
              </div>
            ) : <p className="adminHelp">Click refresh to load admin status.</p>}
          </AdminSection>

          <AdminSection panelId="activity" title="Walkthrough Build Activity" actions={<button className="secondaryButton" onClick={loadBuildStatus}>Refresh Activity</button>}>
            {buildStatus ? (
              <>
                <div className="adminStats">
                  <div><strong>{buildStatus.activity_state?.toUpperCase()}</strong><span>Activity</span></div>
                  <div><strong>{buildStatus.seconds_since_activity ? Math.round(buildStatus.seconds_since_activity) : 0}</strong><span>Seconds idle</span></div>
                  <div><strong>{buildStatus.walkthrough_count || 0}</strong><span>Walkthroughs</span></div>
                  <div><strong>{buildStatus.image_count || 0}</strong><span>Images</span></div>
                </div>
              </>
            ) : <p className="adminHelp">Loading build activity...</p>}
          </AdminSection>

          <AdminSection panelId="advanced" title="Advanced Tools">
            <div style={{ display: "grid", gap: "18px" }}>
              <div>
                <h3>Bulk Query Seeder</h3>
                <textarea className="adminTextArea" value={bulkQueries} onChange={(e) => setBulkQueries(e.target.value)} placeholder="One walkthrough query per line" />
                <button className="startButton" onClick={submitBulkQueries} disabled={adminLoading || !bulkQueries.trim()}>SAVE BULK QUERIES</button>
              </div>
              <div>
                <h3>Walkthrough Taxonomy Index</h3>
                <button className="secondaryButton" onClick={rebuildWalkthroughIndex} disabled={adminLoading}>Sift Existing Walkthroughs</button>
                {taxonomyIndexStatus && (
                  <div className="adminStats compactStats">
                    <div><strong>{taxonomyIndexStatus.stored_walkthrough_count || 0}</strong><span>Stored</span></div>
                    <div><strong>{taxonomyIndexStatus.taxonomy_entries_with_existing_walkthroughs || 0}</strong><span>Matched</span></div>
                    <div><strong>{taxonomyIndexStatus.prospective_taxonomy_entries_without_existing_walkthroughs || 0}</strong><span>Prospective</span></div>
                    <div><strong>{taxonomyIndexStatus.unmatched_existing_walkthrough_count || 0}</strong><span>Unmatched</span></div>
                  </div>
                )}
              </div>
              <div>
                <h3>Bulk Brand Ingestion</h3>
                <textarea className="adminTextArea" value={bulkCatalog} onChange={(e) => setBulkCatalog(e.target.value)} placeholder="Brand | Category" />
                <button className="startButton" onClick={submitBulkCatalog} disabled={adminLoading || !bulkCatalog.trim()}>SAVE BULK CATALOG REQUESTS</button>
              </div>
              <div>
                <h3>Brand + Category Catalog Builder</h3>
                <input className="queryBox" type="text" value={catalogBrand} onChange={(e) => setCatalogBrand(e.target.value)} placeholder="Brand, e.g. Kohler" />
                <input className="queryBox" type="text" value={catalogCategory} onChange={(e) => setCatalogCategory(e.target.value)} placeholder="Category, e.g. Toilets" />
                <textarea className="adminTextArea small" value={catalogModels} onChange={(e) => setCatalogModels(e.target.value)} placeholder="Optional models, one per line" />
                <button className="startButton" onClick={submitCatalogEntry} disabled={adminLoading || !catalogBrand.trim() || !catalogCategory.trim()}>SAVE CATALOG ENTRY</button>
              </div>
              <div>
                <h3>Legacy Image Tools</h3>
                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                  <button className="secondaryButton" onClick={loadCanonicalStatus} disabled={adminLoading}>Load Canonical Status</button>
                  <button className="secondaryButton" onClick={loadImageRegistry} disabled={adminLoading}>Load Image Registry</button>
                  <button className="secondaryButton" onClick={rebuildImageRegistry} disabled={adminLoading}>Rebuild Image Registry</button>
                </div>
              </div>
            </div>
          </AdminSection>

          {imageDirectionEditor && (
            <QcImageDirectionModal
              key={imageDirectionEditor.cacheKey}
              editor={imageDirectionEditor}
              step={qcWalkthroughs[imageDirectionEditor.walkthroughId]?.steps?.[imageDirectionEditor.stepIndex]}
              generating={!!qcImageGenerating[`${imageDirectionEditor.walkthroughId}-${imageDirectionEditor.stepIndex}`]}
              onClose={closeImageDirectionEditor}
              onDraftChange={cacheImageDirectionEditorValue}
              onApply={applyImageDirectionEditor}
              onApplyAndGenerate={applyAndGenerateImageDirection}
            />
          )}

          {adminMessage && (
            <p className="adminMessage">{adminMessage}</p>
          )}

          <button className="secondaryButton" onClick={backToHome}>
            ← Back to App
          </button>
        </main>
      ) : screen === "briefing" ? (
        <main className="clarifyScreen modelBriefingScreen">
          <div className="homeBadge">MODEL-SPECIFIC PREP</div>

          <h1>{selectedBrand} {selectedModel}</h1>

          <section className="brandModelPanel modelBriefingCard" style={{ display: "grid", gridTemplateColumns: "minmax(220px, 360px) 1fr", gap: "24px", alignItems: "start" }}>
            <div className="modelPhotoFrame" style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "220px", background: "#f6f7f8", borderRadius: "18px", overflow: "hidden" }}>
              {overlayData?.product_image_url ? (
                <img
                  className="modelProductImage"
                  style={{ maxWidth: "100%", maxHeight: "260px", objectFit: "contain" }}
                  src={apiAssetUrl(overlayData.product_image_url)}
                  alt={`${selectedBrand} ${selectedModel}`}
                  onError={(e) => { e.currentTarget.style.display = "none"; }}
                />
              ) : (
                <div className="modelPhotoFallback" style={{ padding: "40px", color: "#6b7280", textAlign: "center" }}>
                  Product photo pending<br />
                  <small>Build the product package in Admin to cache the manufacturer photo.</small>
                </div>
              )}
            </div>

            <div className="modelBriefingText">
              <p className="clarifyPrompt">
                Review the model-specific notes before opening the full walkthrough.
              </p>

              <button
                className="secondaryButton"
                onClick={() => setTipsExpanded(!tipsExpanded)}
              >
                Important Model-Specific Installation Tips {tipsExpanded ? "▴" : "▾"}
              </button>

              {tipsExpanded && (
                <div className="overlayGrid modelTipsList">
                  {currentModelTips.length > 0 ? currentModelTips.map((tip, index) => (
                    <div key={`${tip.id || tip.title}-${index}`} className={`overlayCard overlay-${tip.type || "model_specific"}`}>
                      <strong>{tip.title}</strong>
                      <p>{tip.content}</p>
                    </div>
                  )) : (
                    <p>No model-specific tips have been extracted yet.</p>
                  )}
                </div>
              )}

              <div className="clarifyActions">
                {overlayData?.manual_url && (
                  <a
                    className="secondaryButton"
                    href={apiAssetUrl(overlayData.manual_url)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Download Install PDF
                  </a>
                )}

                <button className="startButton" onClick={proceedSpecificInstall} disabled={loading}>
                  {loading ? "BUILDING..." : "PROCEED TO INSTALL"}
                </button>
              </div>
            </div>
          </section>

          <div className="clarifyActions">
            <button className="secondaryButton" onClick={() => { setScreen("home"); setClarifying(true); }}>
              ← Change Brand / Model
            </button>
            <button className="secondaryButton" onClick={backToHome}>
              Start Over
            </button>
          </div>
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

          {productOptions?.requires_branch_selection && (
            <section className="choicePanel">
              <h2>{productOptions.branch_question || "Which type of walkthrough do you need?"}</h2>
              {branchOptions.map((branch) => (
                <label key={branch.branch_id} className={`choiceCard ${selectedBranchId === branch.branch_id ? "choiceSelected" : ""}`}>
                  <input
                    type="radio"
                    name="walkthroughBranch"
                    checked={selectedBranchId === branch.branch_id}
                    onChange={() => {
                      setSelectedBranchId(branch.branch_id);
                      setSelectedBranchQuery(branch.query || branch.target_walkthrough_id || query);
                    }}
                  />
                  <span>
                    <strong>{branch.label}</strong>
                    <small>{branch.notes || branch.query}</small>
                  </span>
                </label>
              ))}
            </section>
          )}

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
                disabled={loading || !selectedBrand || !selectedModel || (productOptions?.requires_branch_selection && !selectedBranchId)}
              >
                {loading ? "LOADING MODEL BRIEFING..." : "VIEW MODEL BRIEFING"}
              </button>
            ) : installMode === "generic" ? (
              <button
                className="startButton"
                onClick={continueGeneric}
                disabled={loading || (productOptions?.requires_branch_selection && !selectedBranchId)}
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
                <strong>{walkthrough.estimated_labor_label}</strong>
                <span> (Generic)</span>
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
                  (overlayData?.overlays || [])
                    .filter((hotspot) => Number(hotspot.step_id || hotspot.stepId || 0) === Number(currentStep.id))
                    .map((hotspot, index) => (
                    <button
                      key={hotspot.id || `${hotspot.title}-${index}`}
                      className={`hotspot hotspot${index + 1}`}
                      style={{
                        left: `${hotspot.x || 50}%`,
                        top: `${hotspot.y || 45}%`
                      }}
                      onClick={() => setActiveHotspot(hotspot)}
                      aria-label={hotspot.label || hotspot.title}
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
                {activeHotspot.manual_url && (
                  <p>
                    <a href={apiAssetUrl(activeHotspot.manual_url)} target="_blank" rel="noreferrer">
                      Open source installation PDF
                    </a>
                  </p>
                )}
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

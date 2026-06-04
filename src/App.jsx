import { useEffect, useState } from "react";
import "./App.css";

const API_URL = "https://rocketsurgery-api.onrender.com";

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


function EditableTextField({
  label,
  value,
  onCommit,
  multiline = false,
  placeholder = "",
  className = "adminTextArea small",
  rows = 3
}) {
  const [draft, setDraft] = useState(value || "");

  useEffect(() => {
    setDraft(value || "");
  }, [value]);

  function commit() {
    const original = value || "";
    if (draft !== original) {
      onCommit(draft);
    }
  }

  return (
    <label className="fieldLabel">
      {label}
      {multiline ? (
        <textarea
          className={className}
          rows={rows}
          value={draft}
          placeholder={placeholder}
          onChange={(event) => setDraft(event.target.value)}
          onBlur={commit}
        />
      ) : (
        <input
          value={draft}
          placeholder={placeholder}
          onChange={(event) => setDraft(event.target.value)}
          onBlur={commit}
        />
      )}
    </label>
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
  const [specificQuery, setSpecificQuery] = useState("");
  const [tipsExpanded, setTipsExpanded] = useState(false);

  const [imageRegistry, setImageRegistry] = useState(null);
  const [promoteFilename, setPromoteFilename] = useState("");
  const [promoteCanonicalKey, setPromoteCanonicalKey] = useState("");
  const [promoteStepNumber, setPromoteStepNumber] = useState(1);

  const [buildStatus, setBuildStatus] = useState(null);

  const [bulkJobList, setBulkJobList] = useState(null);
  const [walkthroughList, setWalkthroughList] = useState([]);
  const [selectedAdminWalkthrough, setSelectedAdminWalkthrough] = useState(null);
  const [repairCorrections, setRepairCorrections] = useState({});
  const [editorDraft, setEditorDraft] = useState(null);
  const [editorDirty, setEditorDirty] = useState(false);
  const [editorSaving, setEditorSaving] = useState(false);
  const [adminPanels, setAdminPanels] = useState({
    repair: true,
    catalog: false,
    reports: false,
    queue: false,
    status: false,
    activity: false,
    advanced: false
  });
  const [catalogPipelineStatus, setCatalogPipelineStatus] = useState(null);
  const [catalogPipelineRunning, setCatalogPipelineRunning] = useState("");
  const [productPackageBrand, setProductPackageBrand] = useState("Niagara");
  const [productPackageModel, setProductPackageModel] = useState("Original Stealth");
  const [productPackageCategory, setProductPackageCategory] = useState("toilet");
  const [productPackageUrl, setProductPackageUrl] = useState("https://niagaracorp.com/products/original-stealth-handle-round/");
  const [productPackageRunning, setProductPackageRunning] = useState(false);
  const [productPackageResult, setProductPackageResult] = useState(null);

  const currentStep = walkthrough?.steps?.[stepIndex];
  const availableBrands = productOptions?.brands || [];
  const selectedBrandRecord = availableBrands.find(
    (item) => item.brand === selectedBrand
  );
  const availableModels = selectedBrandRecord?.models || [];
  const currentModelTips = overlayData?.installation_tips || overlayData?.overlays || [];

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

  async function continueSpecific() {
    const finalQuery = buildSpecificQuery(query, selectedBrand, selectedModel);
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
    loadCatalogPipelineStatus();
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

      let products = [];
      try {
        const productResponse = await fetch(`${API_URL}/catalog/products?category=toilet`, {
          cache: "no-store"
        });
        const productData = await productResponse.json();
        products = productData.products || [];
      } catch (productError) {
        console.warn("Could not load v2 catalog products", productError);
      }

      const productMap = new Map(
        products.map((product) => [
          `${String(product.brand || "").toLowerCase()}::${String(product.model || "").toLowerCase()}`,
          product
        ])
      );

      const mergedItems = (data.items || []).map((item) => {
        const product = productMap.get(`${String(item.brand || "").toLowerCase()}::${String(item.model || "").toLowerCase()}`);
        const photoUrl = product?.photo_url || item.photo?.local_url || "";
        const manualUrl = product?.manual_url || item.manual?.local_url || "";

        return {
          ...item,
          source: product?.source || item.source || "starter_catalog",
          product_page_url: product?.product_page_url || item.photo?.product_page_url || "",
          photo: {
            ...(item.photo || {}),
            status: photoUrl ? "cached" : item.photo?.status || "missing",
            local_url: photoUrl
          },
          manual: {
            ...(item.manual || {}),
            status: manualUrl ? "cached" : item.manual?.status || "missing",
            local_url: manualUrl
          },
          confidence: product?.confidence || item.confidence || "LOW"
        };
      });

      setCatalogPipelineStatus({ ...data, items: mergedItems, products });
      setAdminMessage(`Catalog pipelines loaded: ${mergedItems.length} models.`);
    } catch (error) {
      console.error(error);
      setAdminMessage(`Catalog pipeline status failed: ${error.message}`);
    }
  }

  async function runCatalogPipeline(item, pipeline = "all") {
    const key = `${item.brand}-${item.model}-${pipeline}`;
    setCatalogPipelineRunning(key);
    setAdminMessage(`Running ${pipeline} pipeline for ${item.brand} ${item.model}...`);

    const endpoint = pipeline === "photo"
      ? "/admin/catalog/fetch-product-photo"
      : pipeline === "manual"
        ? "/admin/catalog/fetch-install-manual"
        : pipeline === "overlay"
          ? "/admin/catalog/build-overlay-package"
          : "/admin/catalog/run-model-pipelines";

    try {
      const response = await fetch(`${API_URL}${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          category: "toilet",
          brand: item.brand,
          model: item.model
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.status || "Pipeline request failed.");
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
          correction: repairCorrections[stepId] || ""
        })
      });

      const data = await response.json();

      if (data.walkthrough) {
        setSelectedAdminWalkthrough(data.walkthrough);
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
    if (!editorDraft) {
      return;
    }

    setEditorDraft({
      ...editorDraft,
      [field]: value
    });
    setEditorDirty(true);
  }


  function updateEditorStep(stepId, field, value) {
    if (!editorDraft) {
      return;
    }

    setEditorDraft({
      ...editorDraft,
      steps: (editorDraft.steps || []).map((step) => (
        Number(step.id) === Number(stepId)
          ? { ...step, [field]: value }
          : step
      ))
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

    setEditorSaving(true);
    setAdminMessage("Saving walkthrough...");

    try {
      const response = await fetch(`${API_URL}/admin/save-walkthrough`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          walkthrough: editorDraft
        })
      });

      const data = await response.json();

      if (!response.ok || data.status === "error") {
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


          <AdminSection
            panelId="repair"
            title="Walkthrough Repair Editor"
            actions={
              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
                <span className="adminHelp" style={{ margin: 0 }}>
                  {editorDirty ? "● Unsaved changes" : editorDraft ? "✓ All changes saved" : "Select a walkthrough"}
                </span>
                <button className="secondaryButton" onClick={loadAdminWalkthroughs} disabled={adminLoading}>
                  Refresh Walkthroughs
                </button>
                <button className="startButton" onClick={saveEditorWalkthrough} disabled={!editorDraft || !editorDirty || editorSaving}>
                  {editorSaving ? "Saving..." : "Save Walkthrough"}
                </button>
                <button className="secondaryButton" onClick={previewEditorWalkthrough} disabled={!editorDraft}>
                  Preview Walkthrough
                </button>
              </div>
            }
          >
            <p className="adminHelp">
              Production workspace: select a walkthrough, reorder small thumbnail cards, rewrite step text, regenerate weak images, then save the edited manifest.
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "minmax(220px, 300px) 1fr", gap: "16px" }}>
              <div style={{ display: "grid", gap: "8px", alignContent: "start", maxHeight: "720px", overflow: "auto" }}>
                {(walkthroughList || []).slice(0, 120).map((item) => (
                  <button
                    key={item.walkthrough_id}
                    className="secondaryButton"
                    style={{
                      textAlign: "left",
                      borderColor: editorDraft?.walkthrough_id === item.walkthrough_id ? "#111827" : undefined,
                      background: editorDraft?.walkthrough_id === item.walkthrough_id ? "#eef2ff" : undefined
                    }}
                    onClick={() => loadAdminWalkthrough(item.walkthrough_id)}
                    disabled={adminLoading}
                  >
                    <strong>{displayText(item.title, 70)}</strong>
                    <br />
                    <span style={{ fontSize: "12px", opacity: 0.75 }}>
                      {item.walkthrough_id} · {item.step_count} steps
                    </span>
                  </button>
                ))}
              </div>

              <div>
                {editorDraft ? (
                  <>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "10px", marginBottom: "14px" }}>
                      <EditableTextField
                        label="Walkthrough title"
                        value={editorDraft.title || ""}
                        onCommit={(value) => updateEditorField("title", value)}
                      />
                      <EditableTextField
                        label="Disclaimer"
                        value={editorDraft.disclaimer || ""}
                        onCommit={(value) => updateEditorField("disclaimer", value)}
                        multiline
                        rows={3}
                      />
                    </div>

                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "12px" }}>
                      {(editorDraft.steps || []).map((step, index) => (
                        <div
                          key={`${step.id}-${index}`}
                          style={{
                            border: "1px solid rgba(0,0,0,0.14)",
                            borderRadius: "16px",
                            padding: "12px",
                            background: "rgba(255,255,255,0.88)",
                            display: "grid",
                            gap: "8px"
                          }}
                        >
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "8px" }}>
                            <strong>Step {index + 1}</strong>
                            <div style={{ display: "flex", gap: "6px" }}>
                              <button className="secondaryButton" onClick={() => moveEditorStep(step.id, -1)} disabled={index === 0}>↑</button>
                              <button className="secondaryButton" onClick={() => moveEditorStep(step.id, 1)} disabled={index === (editorDraft.steps || []).length - 1}>↓</button>
                            </div>
                          </div>

                          <div style={{ display: "grid", gridTemplateColumns: step.pendingImageUrl ? "1fr 1fr" : "1fr", gap: "8px" }}>
                            <img
                              src={apiAssetUrl(step.imageUrl)}
                              alt={step.imageLabel || `Step ${step.id}`}
                              style={{ width: "100%", maxHeight: "145px", objectFit: "cover", borderRadius: "12px", border: "1px solid rgba(0,0,0,0.1)" }}
                            />
                            {step.pendingImageUrl && (
                              <img
                                src={apiAssetUrl(step.pendingImageUrl)}
                                alt={`Candidate for step ${step.id}`}
                                style={{ width: "100%", maxHeight: "145px", objectFit: "cover", borderRadius: "12px", border: "2px solid rgba(37,99,235,0.45)" }}
                              />
                            )}
                          </div>

                          <EditableTextField
                            label="Step title / caption"
                            value={step.imageLabel || ""}
                            onCommit={(value) => updateEditorStep(step.id, "imageLabel", value)}
                          />

                          <EditableTextField
                            label="Instruction text"
                            value={step.instruction || ""}
                            onCommit={(value) => updateEditorStep(step.id, "instruction", value)}
                            multiline
                            rows={4}
                          />

                          <EditableTextField
                            label="Detail text"
                            value={step.detail || ""}
                            onCommit={(value) => updateEditorStep(step.id, "detail", value)}
                            multiline
                            rows={4}
                          />

                          <textarea
                            className="adminTextArea small"
                            value={repairCorrections[step.id] || ""}
                            onChange={(event) => setRepairCorrections({ ...repairCorrections, [step.id]: event.target.value })}
                            placeholder="New image prompt or correction, e.g. show copper pipe, remove PVC, add propane torch."
                          />

                          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                            <button className="startButton" onClick={() => regenerateStepImage(step.id)} disabled={adminLoading}>
                              Regenerate Image
                            </button>
                            {step.pendingImageUrl && (
                              <button className="doneButton" onClick={() => acceptStepImage(step.id)} disabled={adminLoading}>
                                Keep New
                              </button>
                            )}
                            <button className="secondaryButton" onClick={() => revertStepImage(step.id)} disabled={adminLoading}>
                              Revert / Discard
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </>
                ) : (
                  <p className="adminHelp">Select a walkthrough to start editing. Click Refresh Walkthroughs if the list is empty.</p>
                )}
              </div>
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
                {catalogPipelineStatus.items.map((item) => (
                  <div key={`${item.brand}-${item.model}`} style={{ border: "1px solid rgba(0,0,0,0.12)", borderRadius: "14px", padding: "12px", background: "white" }}>
                    <strong>{item.brand} {item.model}</strong>
                    <div style={{ fontSize: "12px", marginTop: "6px" }}>
                      Photo: {item.photo?.status || "unknown"} · Manual: {item.manual?.status || "unknown"} · Overlay: {item.overlay?.status || "unknown"}
                    </div>
                    <div style={{ fontSize: "12px" }}>Confidence: <strong>{item.confidence || "UNKNOWN"}</strong></div>
                    {item.source && <div style={{ fontSize: "12px", opacity: 0.7 }}>Source: {item.source}</div>}
                    <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginTop: "8px" }}>
                      <button className="secondaryButton" onClick={() => runCatalogPipeline(item, "all")} disabled={!!catalogPipelineRunning}>
                        {catalogPipelineRunning === `${item.brand}-${item.model}-all` ? "Running..." : "Run All"}
                      </button>
                      {item.photo?.local_url && (
                        <a className="secondaryButton" href={apiAssetUrl(item.photo.local_url)} target="_blank" rel="noreferrer">
                          View Photo
                        </a>
                      )}
                      {item.manual?.local_url && (
                        <a className="secondaryButton" href={apiAssetUrl(item.manual.local_url)} target="_blank" rel="noreferrer">
                          View PDF
                        </a>
                      )}
                      {item.product_page_url && (
                        <a className="secondaryButton" href={item.product_page_url} target="_blank" rel="noreferrer">
                          Product Page
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="adminHelp">Click Refresh Catalog to load available packages and starter models.</p>
            )}
          </AdminSection>

          <AdminSection panelId="reports" title="Package Report Panel">
            {productPackageResult ? (
              <div style={{ display: "grid", gap: "12px" }}>
                <h3 style={{ margin: 0 }}>{productPackageResult.product?.brand || productPackageBrand} {productPackageResult.product?.model || productPackageModel}</h3>
                <div className="adminStats">
                  <div><strong>{productPackageResult.product?.photo_url ? "YES" : "NO"}</strong><span>Photo Found</span></div>
                  <div><strong>{productPackageResult.product?.manual_url ? "YES" : "NO"}</strong><span>Manual Found</span></div>
                  <div><strong>{productPackageResult.discovery?.pdfs?.length || 0}</strong><span>PDF candidates</span></div>
                  <div><strong>{productPackageResult.overlays?.length || productPackageResult.discovery?.overlays?.length || "—"}</strong><span>Overlays</span></div>
                  <div><strong>{productPackageResult.product?.confidence || "UNKNOWN"}</strong><span>Confidence</span></div>
                </div>
                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                  {productPackageResult.product?.photo_url && <a className="secondaryButton" href={apiAssetUrl(productPackageResult.product.photo_url)} target="_blank" rel="noreferrer">View Photo</a>}
                  {productPackageResult.product?.manual_url && <a className="secondaryButton" href={apiAssetUrl(productPackageResult.product.manual_url)} target="_blank" rel="noreferrer">View Manual</a>}
                  {productPackageResult.overlays_json_url && <a className="secondaryButton" href={apiAssetUrl(productPackageResult.overlays_json_url)} target="_blank" rel="noreferrer">View Overlays</a>}
                  {productPackageResult.discovery_json_url && <a className="secondaryButton" href={apiAssetUrl(productPackageResult.discovery_json_url)} target="_blank" rel="noreferrer">View Discovery JSON</a>}
                </div>
              </div>
            ) : (
              <p className="adminHelp">Build or test a product package to see its quality-control report here.</p>
            )}
          </AdminSection>

          <AdminSection
            panelId="queue"
            title="Queue / Worker Controls"
            actions={<button className="secondaryButton" onClick={loadBulkJobList} disabled={adminLoading}>Refresh Queue</button>}
          >
            <div className="adminStats">
              <div><strong>{bulkJobList?.counts?.queued || 0}</strong><span>Queued</span></div>
              <div><strong>{bulkJobList?.counts?.completed || 0}</strong><span>Completed</span></div>
              <div><strong>{bulkJobList?.counts?.failed || 0}</strong><span>Failed</span></div>
              <div><strong>{buildStatus?.activity_state?.toUpperCase() || "UNKNOWN"}</strong><span>Worker activity</span></div>
            </div>
            <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginBottom: "12px" }}>
              <button className="startButton" onClick={() => runQueueLimit(5)} disabled={adminLoading}>Run Next 5</button>
              <button className="startButton" onClick={() => runQueueLimit(20)} disabled={adminLoading}>Run Next 20</button>
              <button className="secondaryButton" onClick={() => runQueueLimit(999)} disabled={adminLoading}>Run All</button>
            </div>
            {bulkJobList ? (
              <div style={{ display: "grid", gap: "10px" }}>
                {["failed", "queued", "completed", "ignored"].map((group) => (
                  <details key={group}>
                    <summary><strong>{group.toUpperCase()}</strong> ({bulkJobList[group]?.length || 0})</summary>
                    <div style={{ display: "grid", gap: "8px", marginTop: "8px" }}>
                      {(bulkJobList[group] || []).slice(0, 30).map((job) => (
                        <div key={`${group}-${job.query_slug || job.query}`} style={{ border: "1px solid rgba(0,0,0,0.12)", borderRadius: "12px", padding: "10px", background: "#fff" }}>
                          <strong>{displayText(job.query, 100)}</strong>
                          {job.error && <div style={{ fontSize: "12px", color: "#8a1f11", overflowWrap: "anywhere" }}>Error: {displayText(job.error, 180)}</div>}
                          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginTop: "8px" }}>
                            <button className="secondaryButton" onClick={() => updateBulkJob(job.query_slug, "retry")} disabled={adminLoading}>Retry</button>
                            <button className="secondaryButton" onClick={() => updateBulkJob(job.query_slug, "ignore")} disabled={adminLoading}>Ignore</button>
                            <button className="secondaryButton" onClick={() => updateBulkJob(job.query_slug, "delete")} disabled={adminLoading}>Delete</button>
                            {job.walkthrough_id && <button className="secondaryButton" onClick={() => loadAdminWalkthrough(job.walkthrough_id)} disabled={adminLoading}>Edit</button>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </details>
                ))}
              </div>
            ) : (
              <p className="adminHelp">Click Refresh Queue to load queue records.</p>
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
                disabled={loading || !selectedBrand || !selectedModel}
              >
                {loading ? "LOADING MODEL BRIEFING..." : "VIEW MODEL BRIEFING"}
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

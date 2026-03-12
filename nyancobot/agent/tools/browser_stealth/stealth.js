/**
 * stealth.js - Browser Fingerprint Evasion Script
 *
 * Inject via page.addInitScript() to evade common bot detection.
 * Based on PinchTab's stealth approach (MIT License).
 *
 * Covers:
 *   - navigator.webdriver removal
 *   - Chrome DevTools (cdc_*) property cleanup
 *   - window.chrome.runtime spoofing
 *   - navigator.permissions.query patching
 *   - navigator.plugins injection
 *   - navigator.languages override
 *   - Canvas fingerprint noise
 *   - WebGL fingerprint spoofing
 *   - Font fingerprint noise
 *   - WebRTC IP leak prevention
 */

(() => {
  "use strict";

  // ================================================================
  // Session-unique seed for deterministic noise (consistent within session)
  // ================================================================
  const SEED = (() => {
    let s = Date.now() ^ (Math.random() * 0xffffffff);
    return () => {
      s ^= s << 13;
      s ^= s >> 17;
      s ^= s << 5;
      return (s >>> 0) / 0xffffffff;
    };
  })();

  // ================================================================
  // 1. navigator.webdriver -> undefined
  // ================================================================
  Object.defineProperty(navigator, "webdriver", {
    get: () => undefined,
    configurable: true,
  });

  // ================================================================
  // 2. Remove Chrome DevTools detection properties (cdc_*)
  // ================================================================
  (() => {
    const cdcPattern = /^cdc_/;
    const clean = (obj) => {
      if (!obj) return;
      try {
        Object.getOwnPropertyNames(obj).forEach((prop) => {
          if (cdcPattern.test(prop)) {
            try {
              delete obj[prop];
            } catch (_) {
              // immutable property; best-effort
            }
          }
        });
      } catch (_) {}
    };
    clean(document);
    clean(window);

    // Also patch document.querySelector to hide $cdc elements
    const origQuerySelector = document.querySelector.bind(document);
    document.querySelector = function (sel) {
      if (typeof sel === "string" && sel.includes("cdc_")) return null;
      return origQuerySelector(sel);
    };
  })();

  // ================================================================
  // 3. window.chrome.runtime spoofing
  // ================================================================
  if (!window.chrome) {
    window.chrome = {};
  }
  if (!window.chrome.runtime) {
    window.chrome.runtime = {
      connect: function () {},
      sendMessage: function () {},
      id: undefined,
    };
  }

  // ================================================================
  // 4. navigator.permissions.query patch
  //    Return "prompt" for "notifications" (default in real browsers)
  // ================================================================
  (() => {
    const origQuery = navigator.permissions.query.bind(navigator.permissions);
    navigator.permissions.query = function (desc) {
      if (desc && desc.name === "notifications") {
        return Promise.resolve({
          state: "prompt",
          onchange: null,
        });
      }
      return origQuery(desc);
    };
  })();

  // ================================================================
  // 5. navigator.plugins - inject standard Chrome plugins
  // ================================================================
  (() => {
    const fakePlugins = [
      {
        name: "PDF Viewer",
        description: "Portable Document Format",
        filename: "internal-pdf-viewer",
        mimeTypes: [
          {
            type: "application/pdf",
            suffixes: "pdf",
            description: "Portable Document Format",
          },
        ],
      },
      {
        name: "Chrome PDF Viewer",
        description: "Portable Document Format",
        filename: "internal-pdf-viewer",
        mimeTypes: [
          {
            type: "application/x-google-chrome-pdf",
            suffixes: "pdf",
            description: "Portable Document Format",
          },
        ],
      },
      {
        name: "Chromium PDF Viewer",
        description: "Portable Document Format",
        filename: "internal-pdf-viewer",
        mimeTypes: [
          {
            type: "application/pdf",
            suffixes: "pdf",
            description: "Portable Document Format",
          },
        ],
      },
      {
        name: "Microsoft Edge PDF Viewer",
        description: "Portable Document Format",
        filename: "internal-pdf-viewer",
        mimeTypes: [
          {
            type: "application/pdf",
            suffixes: "pdf",
            description: "Portable Document Format",
          },
        ],
      },
      {
        name: "WebKit built-in PDF",
        description: "Portable Document Format",
        filename: "internal-pdf-viewer",
        mimeTypes: [
          {
            type: "application/pdf",
            suffixes: "pdf",
            description: "Portable Document Format",
          },
        ],
      },
    ];

    const makeMimeType = (mt, plugin) => {
      const obj = Object.create(MimeType.prototype);
      Object.defineProperties(obj, {
        type: { get: () => mt.type },
        suffixes: { get: () => mt.suffixes },
        description: { get: () => mt.description },
        enabledPlugin: { get: () => plugin },
      });
      return obj;
    };

    const makePlugin = (p) => {
      const plugin = Object.create(Plugin.prototype);
      const mimeTypes = p.mimeTypes.map((mt) => makeMimeType(mt, plugin));
      Object.defineProperties(plugin, {
        name: { get: () => p.name },
        description: { get: () => p.description },
        filename: { get: () => p.filename },
        length: { get: () => mimeTypes.length },
      });
      mimeTypes.forEach((mt, i) => {
        Object.defineProperty(plugin, i, { get: () => mt });
        Object.defineProperty(plugin, mt.type, { get: () => mt });
      });
      plugin.item = (index) => mimeTypes[index] || null;
      plugin.namedItem = (name) =>
        mimeTypes.find((mt) => mt.type === name) || null;
      return plugin;
    };

    const plugins = fakePlugins.map(makePlugin);

    Object.defineProperty(navigator, "plugins", {
      get: () => {
        const arr = Object.create(PluginArray.prototype);
        plugins.forEach((p, i) => {
          Object.defineProperty(arr, i, { get: () => p, enumerable: true });
        });
        Object.defineProperty(arr, "length", {
          get: () => plugins.length,
        });
        arr.item = (i) => plugins[i] || null;
        arr.namedItem = (name) => plugins.find((p) => p.name === name) || null;
        arr.refresh = () => {};
        return arr;
      },
      configurable: true,
    });
  })();

  // ================================================================
  // 6. navigator.languages override (Japanese locale)
  // ================================================================
  Object.defineProperty(navigator, "languages", {
    get: () => ["ja", "ja-JP", "en-US", "en"],
    configurable: true,
  });
  Object.defineProperty(navigator, "language", {
    get: () => "ja",
    configurable: true,
  });

  // ================================================================
  // 7. Canvas fingerprint noise
  //    Inject subtle per-session noise into toDataURL, toBlob, getImageData
  // ================================================================
  (() => {
    const addNoise = (data) => {
      // Modify ~2% of pixels by +-1 in a single channel
      const len = data.length;
      for (let i = 0; i < len; i += 4) {
        if (SEED() < 0.02) {
          const channel = (SEED() * 3) | 0; // 0=R, 1=G, 2=B
          const delta = SEED() < 0.5 ? 1 : -1;
          const idx = i + channel;
          data[idx] = Math.max(0, Math.min(255, data[idx] + delta));
        }
      }
    };

    // Patch CanvasRenderingContext2D.getImageData
    const origGetImageData =
      CanvasRenderingContext2D.prototype.getImageData;
    CanvasRenderingContext2D.prototype.getImageData = function () {
      const imageData = origGetImageData.apply(this, arguments);
      addNoise(imageData.data);
      return imageData;
    };

    // Patch HTMLCanvasElement.toDataURL
    const origToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function () {
      const ctx = this.getContext("2d");
      if (ctx) {
        try {
          const imageData = origGetImageData.call(
            ctx,
            0,
            0,
            this.width,
            this.height
          );
          addNoise(imageData.data);
          ctx.putImageData(imageData, 0, 0);
        } catch (_) {
          // Cross-origin canvas; skip noise
        }
      }
      return origToDataURL.apply(this, arguments);
    };

    // Patch HTMLCanvasElement.toBlob
    const origToBlob = HTMLCanvasElement.prototype.toBlob;
    HTMLCanvasElement.prototype.toBlob = function (callback) {
      const ctx = this.getContext("2d");
      if (ctx) {
        try {
          const imageData = origGetImageData.call(
            ctx,
            0,
            0,
            this.width,
            this.height
          );
          addNoise(imageData.data);
          ctx.putImageData(imageData, 0, 0);
        } catch (_) {}
      }
      return origToBlob.apply(this, arguments);
    };
  })();

  // ================================================================
  // 8. WebGL fingerprint spoofing
  // ================================================================
  (() => {
    const VENDOR = "Intel Inc.";
    const RENDERER = "Intel Iris OpenGL Engine";

    const patchWebGL = (proto) => {
      const origGetParameter = proto.getParameter;
      proto.getParameter = function (param) {
        // UNMASKED_VENDOR_WEBGL = 0x9245
        if (param === 0x9245) return VENDOR;
        // UNMASKED_RENDERER_WEBGL = 0x9246
        if (param === 0x9246) return RENDERER;
        return origGetParameter.call(this, param);
      };

      // Also patch getExtension to ensure WEBGL_debug_renderer_info exists
      const origGetExtension = proto.getExtension;
      proto.getExtension = function (name) {
        if (name === "WEBGL_debug_renderer_info") {
          return {
            UNMASKED_VENDOR_WEBGL: 0x9245,
            UNMASKED_RENDERER_WEBGL: 0x9246,
          };
        }
        return origGetExtension.call(this, name);
      };
    };

    if (typeof WebGLRenderingContext !== "undefined") {
      patchWebGL(WebGLRenderingContext.prototype);
    }
    if (typeof WebGL2RenderingContext !== "undefined") {
      patchWebGL(WebGL2RenderingContext.prototype);
    }
  })();

  // ================================================================
  // 9. Font fingerprint noise (measureText)
  // ================================================================
  (() => {
    const origMeasureText =
      CanvasRenderingContext2D.prototype.measureText;
    CanvasRenderingContext2D.prototype.measureText = function (text) {
      const metrics = origMeasureText.call(this, text);
      // Add +-0.1px noise to width
      const noise = (SEED() - 0.5) * 0.2;
      const origWidth = metrics.width;
      Object.defineProperty(metrics, "width", {
        get: () => origWidth + noise,
        configurable: true,
      });
      return metrics;
    };
  })();

  // ================================================================
  // 10. WebRTC IP leak prevention
  //     Force iceTransportPolicy = 'relay' to prevent local IP exposure
  // ================================================================
  (() => {
    if (typeof RTCPeerConnection === "undefined") return;

    const OrigRTC = RTCPeerConnection;
    window.RTCPeerConnection = function (config, constraints) {
      config = config || {};
      config.iceTransportPolicy = "relay";
      // Remove non-relay ICE servers if none support TURN
      if (config.iceServers) {
        config.iceServers = config.iceServers.filter((server) => {
          const urls = Array.isArray(server.urls)
            ? server.urls
            : [server.urls || server.url];
          return urls.some((u) => typeof u === "string" && u.startsWith("turn"));
        });
      }
      return new OrigRTC(config, constraints);
    };
    window.RTCPeerConnection.prototype = OrigRTC.prototype;
    Object.defineProperty(window, "RTCPeerConnection", {
      writable: false,
      configurable: false,
    });

    // Also patch webkitRTCPeerConnection if it exists
    if (typeof webkitRTCPeerConnection !== "undefined") {
      window.webkitRTCPeerConnection = window.RTCPeerConnection;
    }
  })();

  // ================================================================
  // Additional: Hide automation-related properties
  // ================================================================

  // Remove Playwright/Puppeteer detection markers
  delete window.__playwright;
  delete window.__pw_manual;
  delete window.__PW_inspect;

  // navigator.connection.rtt fix (automation often shows 0)
  if (navigator.connection) {
    Object.defineProperty(navigator.connection, "rtt", {
      get: () => 100,
      configurable: true,
    });
  }

  // navigator.platform fix
  Object.defineProperty(navigator, "platform", {
    get: () => "MacIntel",
    configurable: true,
  });

  // navigator.maxTouchPoints (desktop should be 0)
  Object.defineProperty(navigator, "maxTouchPoints", {
    get: () => 0,
    configurable: true,
  });

  // navigator.hardwareConcurrency (reasonable desktop value)
  Object.defineProperty(navigator, "hardwareConcurrency", {
    get: () => 8,
    configurable: true,
  });

  // navigator.deviceMemory (reasonable desktop value)
  Object.defineProperty(navigator, "deviceMemory", {
    get: () => 8,
    configurable: true,
  });
})();

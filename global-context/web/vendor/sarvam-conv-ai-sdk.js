/* Vendored, bundled (esbuild, IIFE) browser build of npm "sarvam-conv-ai-sdk" v0.0.42 — ConversationAgent +
   BrowserAudioInterface, re-exported as window.SarvamConvAI. Rebuild: see web/vendor/README.md. */
var SarvamConvAI = (() => {
  var __defProp = Object.defineProperty;
  var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __hasOwnProp = Object.prototype.hasOwnProperty;
  var __defNormalProp = (obj, key, value) => key in obj ? __defProp(obj, key, { enumerable: true, configurable: true, writable: true, value }) : obj[key] = value;
  var __require = /* @__PURE__ */ ((x) => typeof require !== "undefined" ? require : typeof Proxy !== "undefined" ? new Proxy(x, {
    get: (a, b) => (typeof require !== "undefined" ? require : a)[b]
  }) : x)(function(x) {
    if (typeof require !== "undefined") return require.apply(this, arguments);
    throw Error('Dynamic require of "' + x + '" is not supported');
  });
  var __commonJS = (cb, mod) => function __require2() {
    try {
      return mod || (0, cb[__getOwnPropNames(cb)[0]])((mod = { exports: {} }).exports, mod), mod.exports;
    } catch (e) {
      throw mod = 0, e;
    }
  };
  var __export = (target, all) => {
    for (var name in all)
      __defProp(target, name, { get: all[name], enumerable: true });
  };
  var __copyProps = (to, from, except, desc) => {
    if (from && typeof from === "object" || typeof from === "function") {
      for (let key of __getOwnPropNames(from))
        if (!__hasOwnProp.call(to, key) && key !== except)
          __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
    }
    return to;
  };
  var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);
  var __publicField = (obj, key, value) => __defNormalProp(obj, typeof key !== "symbol" ? key + "" : key, value);

  // (disabled):ws
  var require_ws = __commonJS({
    "(disabled):ws"() {
    }
  });

  // entry.js
  var entry_exports = {};
  __export(entry_exports, {
    AgentState: () => AgentState,
    BrowserAudioInterface: () => BrowserAudioInterface,
    ConversationAgent: () => ConversationAgent,
    InteractionType: () => InteractionType
  });

  // node_modules/sarvam-conv-ai-sdk/dist/types/types.js
  var AudioEncoding;
  (function(AudioEncoding2) {
    AudioEncoding2["LINEAR16"] = "audio/wav";
  })(AudioEncoding || (AudioEncoding = {}));
  var ServerMsgCategory;
  (function(ServerMsgCategory2) {
    ServerMsgCategory2["MEDIA"] = "media";
    ServerMsgCategory2["ACTION"] = "action";
    ServerMsgCategory2["SYSTEM"] = "system";
    ServerMsgCategory2["EVENT"] = "event";
  })(ServerMsgCategory || (ServerMsgCategory = {}));
  var MsgStatus;
  (function(MsgStatus2) {
    MsgStatus2["PENDING"] = "pending";
    MsgStatus2["COMPLETED"] = "completed";
    MsgStatus2["FAILED"] = "failed";
  })(MsgStatus || (MsgStatus = {}));
  var ClientMsgCategory;
  (function(ClientMsgCategory2) {
    ClientMsgCategory2["MEDIA"] = "media";
    ClientMsgCategory2["ACTION"] = "action";
    ClientMsgCategory2["SYSTEM"] = "system";
  })(ClientMsgCategory || (ClientMsgCategory = {}));
  var MsgOrigin;
  (function(MsgOrigin2) {
    MsgOrigin2["SERVER"] = "server";
    MsgOrigin2["CLIENT"] = "client";
  })(MsgOrigin || (MsgOrigin = {}));
  var ServerMsgType;
  (function(ServerMsgType2) {
    ServerMsgType2["AUDIO_CHUNK"] = "server.media.audio_chunk";
    ServerMsgType2["AUDIO"] = "server.media.audio";
    ServerMsgType2["TEXT"] = "server.media.text";
    ServerMsgType2["TEXT_CHUNK"] = "server.media.text_chunk";
    ServerMsgType2["PING"] = "server.system.ping";
    ServerMsgType2["INTERACTION_END"] = "server.action.interaction_end";
    ServerMsgType2["INTERACTION_CONNECTED"] = "server.action.interaction_connected";
    ServerMsgType2["USER_SPEECH_START"] = "server.event.user_speech_start";
    ServerMsgType2["USER_SPEECH_END"] = "server.event.user_speech_end";
    ServerMsgType2["USER_INTERRUPT"] = "server.event.user_interrupt";
    ServerMsgType2["VARIABLE_UPDATE"] = "server.event.variable_update";
    ServerMsgType2["LANGUAGE_CHANGE"] = "server.event.language_change";
    ServerMsgType2["STATE_TRANSITION"] = "server.event.state_transition";
    ServerMsgType2["TRANSCRIPTION"] = "server.event.transcription";
    ServerMsgType2["KB_QUERY"] = "server.event.kb_query";
    ServerMsgType2["TOOL_CALL"] = "server.event.tool_call";
  })(ServerMsgType || (ServerMsgType = {}));
  var ClientMsgType;
  (function(ClientMsgType2) {
    ClientMsgType2["AUDIO_CHUNK"] = "client.media.audio_chunk";
    ClientMsgType2["TEXT"] = "client.media.text";
    ClientMsgType2["TEXT_CHUNK"] = "client.media.text_chunk";
    ClientMsgType2["AUDIO"] = "client.media.audio";
    ClientMsgType2["INTERACTION_START"] = "client.action.interaction_start";
    ClientMsgType2["INTERACTION_END"] = "client.action.interaction_end";
    ClientMsgType2["VARIABLE_UPDATE"] = "client.action.variable_update";
    ClientMsgType2["LANGUAGE_CHANGE"] = "client.action.language_change";
    ClientMsgType2["STATE_TRANSITION"] = "client.action.state_transition";
    ClientMsgType2["PONG"] = "client.system.pong";
  })(ClientMsgType || (ClientMsgType = {}));
  var InteractionType;
  (function(InteractionType2) {
    InteractionType2["CHAT"] = "chat";
    InteractionType2["CALL"] = "call";
  })(InteractionType || (InteractionType = {}));
  var UserIdentifierType;
  (function(UserIdentifierType2) {
    UserIdentifierType2["PHONE_NUMBER"] = "phone_number";
    UserIdentifierType2["EMAIL"] = "email";
    UserIdentifierType2["CUSTOM"] = "custom";
    UserIdentifierType2["UNKNOWN"] = "unknown";
  })(UserIdentifierType || (UserIdentifierType = {}));
  var Role;
  (function(Role2) {
    Role2["USER"] = "user";
    Role2["BOT"] = "bot";
  })(Role || (Role = {}));

  // node_modules/sarvam-conv-ai-sdk/dist/types/state.js
  var AgentState;
  (function(AgentState2) {
    AgentState2["IDLE"] = "idle";
    AgentState2["CONNECTING"] = "connecting";
    AgentState2["CONNECTED"] = "connected";
    AgentState2["LISTENING"] = "listening";
    AgentState2["SPEAKING"] = "speaking";
    AgentState2["ERROR"] = "error";
  })(AgentState || (AgentState = {}));

  // node_modules/sarvam-conv-ai-sdk/dist/types/errors.js
  var SDKError = class extends Error {
    constructor(message, code, statusCode) {
      super(message);
      /** Error code for programmatic handling */
      __publicField(this, "code");
      /** HTTP status code if applicable */
      __publicField(this, "statusCode");
      this.name = "SDKError";
      this.code = code;
      this.statusCode = statusCode;
      if (Error.captureStackTrace) {
        Error.captureStackTrace(this, this.constructor);
      }
    }
  };
  var RateLimitError = class extends SDKError {
    constructor(message, retryAfter = 60) {
      super(message, "RATE_LIMITED", 429);
      /** Number of seconds to wait before retrying (from Retry-After header) */
      __publicField(this, "retryAfter");
      this.name = "RateLimitError";
      this.retryAfter = retryAfter;
    }
  };
  var AuthenticationError = class extends SDKError {
    constructor(message) {
      super(message, "AUTHENTICATION_FAILED", 401);
      this.name = "AuthenticationError";
    }
  };
  var ForbiddenError = class extends SDKError {
    constructor(message) {
      super(message, "FORBIDDEN", 403);
      this.name = "ForbiddenError";
    }
  };
  var NotFoundError = class extends SDKError {
    constructor(message) {
      super(message, "NOT_FOUND", 404);
      this.name = "NotFoundError";
    }
  };
  var ServerError = class extends SDKError {
    constructor(message, statusCode = 500) {
      super(message, "SERVER_ERROR", statusCode);
      this.name = "ServerError";
    }
  };

  // node_modules/sarvam-conv-ai-sdk/dist/utils/message.js
  function createStartInteractionMessageFromConfig(config) {
    return {
      type: ClientMsgType.INTERACTION_START,
      origin: MsgOrigin.CLIENT,
      timestamp: Date.now() / 1e3,
      agent_variables: config.agent_variables,
      initial_language_name: config.initial_language_name,
      initial_bot_message: config.initial_bot_message,
      initial_state_name: config.initial_state_name
    };
  }
  function parseServerMessage(data) {
    if (!data || typeof data !== "object") {
      throw new Error("Invalid message: must be an object");
    }
    if (!data.type) {
      throw new Error("Invalid message: missing 'type' field");
    }
    switch (data.type) {
      case ServerMsgType.TEXT_CHUNK:
      case ServerMsgType.TEXT:
      case ServerMsgType.AUDIO_CHUNK:
      case ServerMsgType.USER_INTERRUPT:
      case ServerMsgType.INTERACTION_END:
      case ServerMsgType.INTERACTION_CONNECTED:
      case ServerMsgType.PING:
        return data;
      default:
        console.warn(`[SDK] Unknown server message type: ${data.type}`);
        console.warn("[SDK] Full message:", JSON.stringify(data, null, 2));
        return data;
    }
  }

  // node_modules/sarvam-conv-ai-sdk/dist/utils/socket.js
  function isReactNative() {
    return typeof navigator !== "undefined" && navigator.product === "ReactNative";
  }
  function getWebSocket() {
    if (isReactNative()) {
      if (typeof global !== "undefined" && global.WebSocket) {
        return global.WebSocket;
      }
      if (typeof window !== "undefined" && window.WebSocket) {
        return window.WebSocket;
      }
    }
    if (typeof window !== "undefined" && typeof window.WebSocket !== "undefined") {
      return window.WebSocket;
    }
    if (typeof __require !== "undefined" && typeof process !== "undefined") {
      try {
        const ws = require_ws();
        return ws;
      } catch (error) {
        throw new Error("WebSocket is not available. In Node.js, please install ws package: npm install ws");
      }
    }
    throw new Error("WebSocket is not available. Please ensure you're in a supported environment.");
  }

  // node_modules/sarvam-conv-ai-sdk/dist/modules/socket-manager.js
  var SocketManager = class {
    constructor(options) {
      __publicField(this, "apiKey");
      __publicField(this, "config");
      __publicField(this, "baseUrl");
      __publicField(this, "interactionId");
      __publicField(this, "referenceId");
      __publicField(this, "customHeaders");
      // Callbacks
      __publicField(this, "eventCallback");
      __publicField(this, "textCallback");
      __publicField(this, "transcriptCallback");
      __publicField(this, "startCallback");
      __publicField(this, "endCallback");
      __publicField(this, "stateCallback");
      __publicField(this, "telemetryCallback");
      // Internal state
      __publicField(this, "ws");
      // WebSocket instance (type varies by environment)
      __publicField(this, "shouldStop", false);
      __publicField(this, "websocketSendQueue", []);
      __publicField(this, "disconnectedEvent");
      __publicField(this, "connectedEvent");
      // Agent state tracking
      __publicField(this, "currentState", AgentState.IDLE);
      // Telemetry timing
      __publicField(this, "sessionStartTime");
      __publicField(this, "wsConnectStartTime");
      __publicField(this, "signedUrlStartTime");
      __publicField(this, "firstAudioSent", false);
      __publicField(this, "firstAudioReceived", false);
      // Track who initiated session end: "user" | "agent" | "network" | "error"
      __publicField(this, "sessionEndInitiator");
      // Network monitoring
      __publicField(this, "offlineStartTime");
      __publicField(this, "boundOfflineHandler");
      __publicField(this, "boundOnlineHandler");
      if (!options.config) {
        throw new Error("config must be provided");
      }
      this.apiKey = options.apiKey;
      this.config = options.config;
      this.baseUrl = options.baseUrl || "https://apps.sarvam.ai/api/app-runtime/";
      this.eventCallback = options.eventCallback;
      this.textCallback = options.textCallback;
      this.transcriptCallback = options.transcriptCallback;
      this.startCallback = options.startCallback;
      this.endCallback = options.endCallback;
      this.stateCallback = options.stateCallback;
      this.telemetryCallback = options.telemetryCallback;
      this.customHeaders = options.customHeaders;
    }
    /**
     * Emit a telemetry event to the consumer's callback.
     * No-op if telemetryCallback is not provided.
     */
    emitTelemetry(name, properties) {
      if (!this.telemetryCallback)
        return;
      const event = {
        name,
        timestamp: Date.now(),
        sessionId: this.referenceId,
        interactionId: this.interactionId,
        properties
      };
      try {
        this.telemetryCallback(event);
      } catch (error) {
        console.error("[SDK] Error in telemetryCallback:", error);
      }
    }
    /**
     * Get the reference ID (call SID)
     */
    get reference_id() {
      if (!this.referenceId) {
        throw new Error("Reference ID is not set");
      }
      return this.referenceId;
    }
    set reference_id(referenceId) {
      this.referenceId = referenceId;
    }
    /**
     * Check if the WebSocket connection is closed
     */
    isWsClosed() {
      const CLOSED = 3;
      return !this.ws || this.ws.readyState === CLOSED;
    }
    /**
     * Start the conversation session.
     *
     * This method:
     * 1. Gets a signed WebSocket URL via HTTP GET
     * 2. Connects to the WebSocket
     * 3. Sends the interaction_start message
     * 4. Starts the message receive loop
     */
    async start() {
      this.sessionStartTime = Date.now();
      this.firstAudioSent = false;
      this.firstAudioReceived = false;
      this.startNetworkMonitoring();
      this.setState(AgentState.CONNECTING);
      this.emitTelemetry("session_started", {});
      const { signedUrl, referenceId } = await this.getSignedUrl();
      this.reference_id = referenceId;
      console.log("[SDK] Got signed URL:", signedUrl);
      this.shouldStop = false;
      this.disconnectedEvent = this.createEvent();
      this.connectedEvent = this.createEvent();
      const wsUrl = this.augmentWsUrlWithParams(signedUrl);
      console.log("[SDK] Final WebSocket URL:", wsUrl);
      this.emitTelemetry("ws_connecting", {});
      this.wsConnectStartTime = Date.now();
      this.runWebSocketLoop(wsUrl);
      if (this.startCallback) {
        await this.startCallback();
      }
    }
    /**
     * Stop the conversation session.
     *
     * This method:
     * - Closes the WebSocket connection
     * - Cancels background tasks
     * - Cleans up resources
     */
    async stop() {
      if (!this.sessionEndInitiator) {
        this.sessionEndInitiator = "user";
      }
      this.shouldStop = true;
      this.stopNetworkMonitoring();
      await this.onStop();
      if (!this.isWsClosed() && this.ws) {
        this.ws.close();
      }
      if (this.disconnectedEvent && !this.disconnectedEvent.promise) {
        this.disconnectedEvent.resolve();
      }
      this.setState(AgentState.IDLE);
      if (this.endCallback) {
        await this.endCallback();
      }
    }
    /**
     * Hook for subclasses to perform cleanup on stop
     */
    async onStop() {
    }
    /**
     * Wait until the WebSocket disconnects or the agent is stopped
     */
    async waitForDisconnect() {
      if (!this.disconnectedEvent) {
        return;
      }
      await this.disconnectedEvent.promise;
    }
    /**
     * Wait until the WebSocket connection is established.
     *
     * @param timeout - Maximum seconds to wait. If null, wait indefinitely.
     * @returns True if the connection is established within the timeout, false otherwise.
     */
    async waitForConnect(timeout) {
      if (this.isConnected()) {
        return true;
      }
      if (!this.connectedEvent) {
        this.connectedEvent = this.createEvent();
      }
      try {
        if (timeout !== void 0) {
          await Promise.race([
            this.connectedEvent.promise,
            new Promise((_, reject) => setTimeout(() => reject(new Error("Timeout")), timeout * 1e3))
          ]);
        } else {
          await this.connectedEvent.promise;
        }
      } catch {
        return this.isConnected();
      }
      return this.isConnected();
    }
    /**
     * Check if the WebSocket is currently connected.
     *
     * @returns True if connected, false otherwise
     */
    isConnected() {
      return !this.isWsClosed();
    }
    /**
     * Get the current interaction identifier for clients.
     *
     * In this SDK, the server associates the interaction with a server-side
     * call session identifier. We expose the same value for client reference.
     */
    getInteractionId() {
      return this.interactionId;
    }
    /**
     * Get the current agent state
     */
    getState() {
      return this.currentState;
    }
    /**
     * Set the agent state and notify callback if changed
     */
    setState(newState) {
      if (this.currentState === newState) {
        return;
      }
      const previousState = this.currentState;
      this.currentState = newState;
      this.emitTelemetry("state_changed", {
        from: previousState,
        to: newState
      });
      if (this.stateCallback) {
        this.stateCallback(newState, previousState);
      }
    }
    /**
     * Create a promise-based event
     */
    createEvent() {
      let resolve;
      const promise = new Promise((res) => {
        resolve = res;
      });
      return { resolve, promise };
    }
    /**
     * Construct the URL for getting signed WebSocket URL
     */
    constructUrl() {
      return `${this.baseUrl}orgs/${this.config.org_id}/workspaces/${this.config.workspace_id}/apps/${this.config.app_id}/url`;
    }
    /**
     * Helper to add query parameters to a URL string (React Native compatible)
     */
    addQueryParam(urlStr, key, value) {
      const separator = urlStr.includes("?") ? "&" : "?";
      return `${urlStr}${separator}${encodeURIComponent(key)}=${encodeURIComponent(value)}`;
    }
    /**
     * Add common user identifier params to URL string
     */
    addUserIdentifierParamsToString(urlStr) {
      let result = this.addQueryParam(urlStr, "user_identifier", this.config.user_identifier);
      result = this.addQueryParam(result, "user_identifier_type", this.config.user_identifier_type);
      return result;
    }
    /**
     * Append required query params for the WebSocket connect URL
     * Note: user_identifier params are already added in getSignedUrl()
     */
    augmentWsUrlWithParams(wsUrl) {
      return this.addQueryParam(wsUrl, "interaction_type", this.config.interaction_type);
    }
    /**
     * Get authenticated WebSocket URL and reference id from the API.
     *
     * Makes an HTTP GET request to get a time-limited signed URL for
     * secure WebSocket connections without exposing the API key.
     *
     * @returns A tuple of (signed_websocket_url, reference_id)
     * @throws Error if the HTTP request fails
     */
    async getSignedUrl() {
      this.signedUrlStartTime = Date.now();
      this.emitTelemetry("signed_url_requested", {});
      let requestUrl = this.constructUrl();
      if (this.config.interaction_type) {
        requestUrl = this.addQueryParam(requestUrl, "interaction_type", this.config.interaction_type);
      }
      if (this.config.version) {
        requestUrl = this.addQueryParam(requestUrl, "version", String(this.config.version));
      }
      console.log("[SDK] Fetching signed URL from:", requestUrl);
      const headers = {
        "X-API-Key": this.apiKey
      };
      this.addCustomHeaders(headers);
      const fetchOptions = {
        method: "GET",
        headers
      };
      const response = await fetch(requestUrl, fetchOptions);
      if (!response.ok) {
        const errorText = await response.text().catch(() => "");
        const durationMs2 = Date.now() - (this.signedUrlStartTime || Date.now());
        this.emitTelemetry("signed_url_failed", {
          error: `${response.status} ${errorText}`,
          durationMs: durationMs2
        });
        switch (response.status) {
          case 429: {
            const retryAfterHeader = response.headers.get("x-retry-after");
            const retryAfter = retryAfterHeader ? parseInt(retryAfterHeader, 10) : 60;
            throw new RateLimitError(`Rate limit exceeded. ${errorText || "Please try again later."}`, isNaN(retryAfter) ? 60 : retryAfter);
          }
          case 401:
            throw new AuthenticationError(`Authentication failed: ${errorText || "Invalid or missing API key"}`);
          case 403:
            throw new ForbiddenError(`Access forbidden: ${errorText || "Insufficient permissions"}`);
          case 404:
            throw new NotFoundError(`Resource not found: ${errorText || "The specified app, workspace, or organization was not found"}`);
          case 500:
          case 502:
          case 503:
          case 504:
            throw new ServerError(`Server error: ${errorText || "Internal server error"}`, response.status);
          default:
            throw new Error(`Failed to get signed URL: ${response.status} ${errorText}`);
        }
      }
      let data;
      try {
        const responseText = await response.text();
        data = responseText ? JSON.parse(responseText) : null;
      } catch (error) {
        throw new Error(`Failed to parse JSON response: ${error instanceof Error ? error.message : String(error)}`);
      }
      if (!data || !data.url || !data.reference_id) {
        const versionHint = this.config.version ? `Version ${this.config.version} is specified.` : `No version specified. Using latest committed version.`;
        throw new Error(`Invalid response from API: ${JSON.stringify(data)}. Expected object with 'url' and 'reference_id' properties. ${versionHint} This may indicate the app has no committed version or the app_id/org_id/workspace_id is incorrect.`);
      }
      const signedUrl = data.url;
      const referenceId = data.reference_id;
      const durationMs = Date.now() - (this.signedUrlStartTime || Date.now());
      this.emitTelemetry("signed_url_received", { durationMs });
      let modifiedUrl = this.addUserIdentifierParamsToString(signedUrl);
      modifiedUrl = this.modifySignedUrlString(modifiedUrl);
      return {
        signedUrl: modifiedUrl,
        referenceId
      };
    }
    /**
     * Add custom headers to API requests.
     * Merges any custom headers provided in constructor options.
     */
    addCustomHeaders(headers) {
      if (this.customHeaders) {
        Object.assign(headers, this.customHeaders);
      }
    }
    /**
     * Hook for subclasses to modify the signed URL
     */
    modifySignedUrlString(url) {
      return url;
    }
    /**
     * Flush send queue to WebSocket
     */
    async flushSendQueue() {
      const OPEN = 1;
      if (this.isWsClosed() || !this.ws || this.ws.readyState !== OPEN) {
        return;
      }
      while (this.websocketSendQueue.length > 0) {
        const message = this.websocketSendQueue.shift();
        const messageJson = JSON.stringify(message);
        this.ws.send(messageJson);
      }
    }
    /**
     * Check if we're running in a React Native environment.
     */
    isReactNative() {
      return typeof navigator !== "undefined" && navigator.product === "ReactNative";
    }
    /**
     * Start listening to network online/offline events.
     * Works in browser environments only (React Native should use NetInfo).
     */
    startNetworkMonitoring() {
      if (typeof window === "undefined" || typeof window.addEventListener !== "function") {
        return;
      }
      this.boundOfflineHandler = () => {
        this.offlineStartTime = Date.now();
        this.sessionEndInitiator = "network";
        this.emitTelemetry("network_offline", {});
      };
      this.boundOnlineHandler = () => {
        const offlineDurationMs = this.offlineStartTime ? Date.now() - this.offlineStartTime : void 0;
        this.offlineStartTime = void 0;
        this.emitTelemetry("network_online", { offlineDurationMs });
      };
      window.addEventListener("offline", this.boundOfflineHandler);
      window.addEventListener("online", this.boundOnlineHandler);
    }
    /**
     * Stop listening to network events and clean up.
     */
    stopNetworkMonitoring() {
      if (typeof window === "undefined" || typeof window.removeEventListener !== "function") {
        return;
      }
      if (this.boundOfflineHandler) {
        window.removeEventListener("offline", this.boundOfflineHandler);
        this.boundOfflineHandler = void 0;
      }
      if (this.boundOnlineHandler) {
        window.removeEventListener("online", this.boundOnlineHandler);
        this.boundOnlineHandler = void 0;
      }
      this.offlineStartTime = void 0;
    }
    /**
     * Main WebSocket loop for receiving and processing messages
     */
    async runWebSocketLoop(wsUrl) {
      return new Promise((resolve, reject) => {
        const WebSocketClass = getWebSocket();
        const isRN = this.isReactNative();
        const isBrowser = !isRN && typeof window !== "undefined" && typeof window.WebSocket !== "undefined";
        const wsOptions = {};
        const ws = Object.keys(wsOptions).length > 0 ? new WebSocketClass(wsUrl, wsOptions) : new WebSocketClass(wsUrl);
        this.ws = ws;
        const OPEN = 1;
        if (isBrowser || isRN) {
          ws.addEventListener("open", async () => {
            try {
              const connectDurationMs = Date.now() - (this.wsConnectStartTime || Date.now());
              this.emitTelemetry("ws_connected", {
                durationMs: connectDurationMs
              });
              await this.sendInteractionStart();
              await this.onWebSocketOpen();
              this.flushSendQueue();
              setInterval(() => this.flushSendQueue(), 100);
            } catch (error) {
              reject(error);
            }
          });
          ws.addEventListener("message", async (event) => {
            try {
              const messageStr = typeof event.data === "string" ? event.data : event.data.toString();
              const message = JSON.parse(messageStr);
              await this.routeMessage(message);
            } catch (error) {
              console.error("Error processing WebSocket message:", error);
              this.emitTelemetry("error", {
                type: "message_processing",
                message: error instanceof Error ? error.message : String(error)
              });
            }
          });
          ws.addEventListener("error", (error) => {
            console.error("WebSocket error:", error);
            const errorMessage = isRN && error.message ? error.message : "WebSocket connection error";
            if (isRN && error.message) {
              console.error("WebSocket error message from React Native:", error.message);
            }
            this.sessionEndInitiator = "error";
            this.emitTelemetry("ws_error", { error: errorMessage });
            this.setState(AgentState.ERROR);
            reject(new Error("WebSocket connection error"));
          });
          ws.addEventListener("close", (event) => {
            const sessionDurationMs = this.sessionStartTime ? Date.now() - this.sessionStartTime : 0;
            const initiator = this.sessionEndInitiator || "network";
            this.emitTelemetry("ws_disconnected", {
              code: event.code,
              reason: event.reason || void 0,
              wasClean: event.wasClean
            });
            this.emitTelemetry("session_ended", {
              durationMs: sessionDurationMs,
              initiatedBy: initiator,
              reason: event.reason || (event.wasClean ? "clean_close" : "connection_lost")
            });
            this.stopNetworkMonitoring();
            this.sessionEndInitiator = void 0;
            this.ws = void 0;
            this.shouldStop = true;
            if (this.disconnectedEvent) {
              this.disconnectedEvent.resolve();
            }
            resolve();
          });
        } else {
          ws.on("open", async () => {
            try {
              const connectDurationMs = Date.now() - (this.wsConnectStartTime || Date.now());
              this.emitTelemetry("ws_connected", {
                durationMs: connectDurationMs
              });
              await this.sendInteractionStart();
              await this.onWebSocketOpen();
              this.flushSendQueue();
              setInterval(() => this.flushSendQueue(), 100);
            } catch (error) {
              reject(error);
            }
          });
          ws.on("message", async (data) => {
            try {
              const messageStr = data.toString();
              const message = JSON.parse(messageStr);
              await this.routeMessage(message);
            } catch (error) {
              console.error("Error processing WebSocket message:", error);
              this.emitTelemetry("error", {
                type: "message_processing",
                message: error instanceof Error ? error.message : String(error)
              });
            }
          });
          ws.on("error", (error) => {
            console.error("WebSocket error:", error);
            this.sessionEndInitiator = "error";
            this.emitTelemetry("ws_error", { error: error.message });
            this.setState(AgentState.ERROR);
            reject(error);
          });
          ws.on("close", (code, reason) => {
            const sessionDurationMs = this.sessionStartTime ? Date.now() - this.sessionStartTime : 0;
            const initiator = this.sessionEndInitiator || "network";
            const reasonStr = reason?.toString() || void 0;
            this.emitTelemetry("ws_disconnected", {
              code,
              reason: reasonStr
            });
            this.emitTelemetry("session_ended", {
              durationMs: sessionDurationMs,
              initiatedBy: initiator,
              reason: reasonStr || "connection_closed"
            });
            this.stopNetworkMonitoring();
            this.sessionEndInitiator = void 0;
            this.ws = void 0;
            this.shouldStop = true;
            if (this.disconnectedEvent) {
              this.disconnectedEvent.resolve();
            }
            resolve();
          });
        }
      });
    }
    /**
     * Hook for subclasses to perform actions after WebSocket opens
     */
    async onWebSocketOpen() {
    }
    /**
     * Send the interaction start message
     */
    async sendInteractionStart() {
      if (!this.ws) {
        throw new Error("WebSocket not connected");
      }
      const message = createStartInteractionMessageFromConfig(this.config);
      if (!this.isWsClosed()) {
        const messageJson = JSON.stringify(message);
        this.ws.send(messageJson);
      }
    }
    /**
     * Route incoming messages to appropriate handlers
     */
    async routeMessage(message) {
      try {
        const parsed = parseServerMessage(message);
        if (parsed.type === ServerMsgType.TEXT) {
          await this.handleText(parsed);
        } else if (parsed.type === ServerMsgType.TRANSCRIPTION) {
          await this.handleTranscript(parsed);
        } else if (parsed.type === ServerMsgType.INTERACTION_END) {
          await this.handleInteractionEnd(parsed);
        } else if (parsed.type === ServerMsgType.PING) {
          await this.handlePing(parsed);
        } else if (parsed.type === ServerMsgType.INTERACTION_CONNECTED) {
          await this.handleInteractionStartAcknowledgement(parsed);
        } else {
          await this.handleCustomMessage(parsed);
        }
      } catch (error) {
        console.error("Failed to parse server message:", error);
        console.error("Raw message:", message);
        this.emitTelemetry("error", {
          type: "message_parse",
          message: error instanceof Error ? error.message : String(error)
        });
      }
    }
    /**
     * Hook for subclasses to handle custom message types
     */
    async handleCustomMessage(message) {
      await this.handleEvent(message);
    }
    /**
     * Handle text message from the agent
     */
    async handleText(textMsg) {
      try {
        if (this.textCallback) {
          await this.textCallback(textMsg);
        }
      } catch (error) {
        console.error("Error handling text message:", error);
      }
    }
    /**
     * Handle transcript message from the agent
     */
    async handleTranscript(transcriptMsg) {
      try {
        if (this.transcriptCallback) {
          await this.transcriptCallback(transcriptMsg);
        }
      } catch (error) {
        console.error("Error handling transcript message:", error);
      }
    }
    /**
     * Handle event message from the agent
     */
    async handleEvent(event) {
      if (this.eventCallback) {
        await this.eventCallback(event);
      }
    }
    /**
     * Handle interaction connected event from server
     */
    async handleInteractionStartAcknowledgement(event) {
      this.interactionId = event.interaction_id;
      this.emitTelemetry("interaction_connected", {
        interactionId: event.interaction_id
      });
      this.setState(AgentState.CONNECTED);
      this.setState(AgentState.LISTENING);
      if (this.connectedEvent) {
        this.connectedEvent.resolve();
      } else {
        console.warn("[SDK] connectedEvent was not set!");
      }
    }
    /**
     * Handle interaction end message
     */
    async handleInteractionEnd(_endMsg) {
      this.sessionEndInitiator = "agent";
      this.setState(AgentState.IDLE);
      if (this.endCallback) {
        await this.endCallback();
      }
    }
    /**
     * Handle ping message and send pong response
     */
    async handlePing(pingMsg) {
      try {
        if (!this.isWsClosed() && this.ws) {
          const pong = {
            type: ClientMsgType.PONG,
            origin: MsgOrigin.CLIENT,
            timestamp: Date.now() / 1e3,
            event_id: pingMsg.event_id
          };
          const pongJson = JSON.stringify(pong);
          this.ws.send(pongJson);
        }
      } catch (error) {
        console.error("Error handling ping:", error);
      }
    }
  };

  // node_modules/sarvam-conv-ai-sdk/dist/utils/buffer.js
  function base64ToUint8Array(base64) {
    if (typeof Buffer !== "undefined" && Buffer.from) {
      const buffer = Buffer.from(base64, "base64");
      const freshArray = new Uint8Array(buffer.length);
      for (let i = 0; i < buffer.length; i++) {
        freshArray[i] = buffer[i];
      }
      return freshArray;
    } else {
      const binaryString = atob(base64);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }
      return bytes;
    }
  }
  function uint8ArrayToBase64(bytes) {
    if (typeof Buffer !== "undefined" && Buffer.isBuffer && Buffer.isBuffer(bytes)) {
      return bytes.toString("base64");
    }
    let uint8Array;
    if (bytes instanceof ArrayBuffer) {
      uint8Array = new Uint8Array(bytes);
    } else if (bytes instanceof Uint8Array) {
      uint8Array = bytes;
    } else {
      uint8Array = new Uint8Array(bytes);
    }
    if (typeof Buffer !== "undefined" && Buffer.from) {
      return Buffer.from(uint8Array).toString("base64");
    } else {
      let binary = "";
      for (let i = 0; i < uint8Array.length; i++) {
        binary += String.fromCharCode(uint8Array[i]);
      }
      return btoa(binary);
    }
  }

  // node_modules/sarvam-conv-ai-sdk/dist/utils/audio-queue.js
  var AudioQueue = class {
    constructor(handler, options) {
      __publicField(this, "queue", []);
      __publicField(this, "shouldStop", false);
      __publicField(this, "processing", false);
      __publicField(this, "handler");
      __publicField(this, "resolveWaiting");
      __publicField(this, "sampleRate");
      __publicField(this, "headroomMs");
      __publicField(this, "sleepTimer");
      __publicField(this, "resolveSleep");
      this.handler = handler;
      this.sampleRate = options?.sampleRate ?? 16e3;
      this.headroomMs = options?.headroomMs ?? 30;
    }
    /**
     * Add an audio message to the queue
     */
    enqueue(msg) {
      this.queue.push(msg);
      if (this.resolveWaiting) {
        this.resolveWaiting();
        this.resolveWaiting = void 0;
      }
    }
    /**
     * Start processing the queue
     */
    start() {
      if (this.processing) {
        return;
      }
      this.shouldStop = false;
      this.processing = true;
      this.processQueue();
    }
    /**
     * Stop processing the queue
     */
    stop() {
      this.shouldStop = true;
      this.processing = false;
      this.cancelSleep();
      if (this.resolveWaiting) {
        this.resolveWaiting();
        this.resolveWaiting = void 0;
      }
    }
    /**
     * Clear all pending messages from the queue
     */
    clear() {
      this.queue = [];
      this.cancelSleep();
    }
    /**
     * Get the current queue length
     */
    get length() {
      return this.queue.length;
    }
    /**
     * Calculate playback duration of a chunk in milliseconds from its PCM data.
     * 16-bit PCM = 2 bytes per sample.
     */
    chunkDurationMs(msg) {
      if (!msg.audio_base64)
        return 0;
      try {
        const bytes = base64ToUint8Array(msg.audio_base64);
        const samples = bytes.length / 2;
        const rate = msg.sample_rate ?? this.sampleRate;
        return samples / rate * 1e3;
      } catch {
        return 0;
      }
    }
    cancelSleep() {
      if (this.sleepTimer != null) {
        clearTimeout(this.sleepTimer);
        this.sleepTimer = void 0;
      }
      if (this.resolveSleep) {
        this.resolveSleep();
        this.resolveSleep = void 0;
      }
    }
    sleep(ms) {
      if (ms <= 0)
        return Promise.resolve();
      return new Promise((resolve) => {
        this.resolveSleep = resolve;
        this.sleepTimer = setTimeout(() => {
          this.sleepTimer = void 0;
          this.resolveSleep = void 0;
          resolve();
        }, ms);
      });
    }
    /**
     * Process messages from the queue, pacing delivery to match playback speed.
     */
    async processQueue() {
      while (!this.shouldStop) {
        while (this.queue.length > 0 && !this.shouldStop) {
          const msg = this.queue.shift();
          const durationMs = this.chunkDurationMs(msg);
          try {
            await this.handler(msg);
          } catch (error) {
            console.error("Error processing audio message:", error);
          }
          if (this.shouldStop)
            break;
          const paceMs = durationMs - this.headroomMs;
          if (paceMs > 0) {
            await this.sleep(paceMs);
          }
        }
        if (this.shouldStop)
          break;
        await new Promise((resolve) => {
          this.resolveWaiting = resolve;
        });
      }
      this.processing = false;
    }
  };

  // node_modules/sarvam-conv-ai-sdk/dist/modules/voice-agent.js
  var _VoiceAgent = class _VoiceAgent extends SocketManager {
    constructor(options) {
      super({
        apiKey: options.apiKey,
        config: options.config,
        eventCallback: options.eventCallback,
        startCallback: options.startCallback,
        endCallback: options.endCallback,
        textCallback: options.textCallback,
        transcriptCallback: options.transcriptCallback,
        stateCallback: options.stateCallback,
        telemetryCallback: options.telemetryCallback,
        baseUrl: options.baseUrl,
        platform: options.platform,
        customHeaders: options.customHeaders
      });
      __publicField(this, "audioInterface");
      __publicField(this, "audioCallback");
      __publicField(this, "audioLevelCallback");
      __publicField(this, "audioQueue");
      __publicField(this, "audioWarningLogged", false);
      // Mute state
      __publicField(this, "_isMuted", false);
      __publicField(this, "silenceInterval", null);
      __publicField(this, "silenceChunk", null);
      // Track whether server has signaled end of utterance (COMPLETED)
      __publicField(this, "utteranceCompleted", false);
      // Total audio duration (ms) pushed to the playback interface since SPEAKING started
      __publicField(this, "playbackAudioMs", 0);
      // Timestamp when we started pushing audio for this utterance
      __publicField(this, "playbackStartedAt", 0);
      // Timer that fires when estimated playback should be done
      __publicField(this, "playbackDrainTimer", null);
      this.audioCallback = options.audioCallback;
      this.audioInterface = options.audioInterface;
      this.audioLevelCallback = options.audioLevelCallback;
      this.audioQueue = new AudioQueue(async (msg) => {
        await this.handleAudio(msg);
      }, { sampleRate: options.config.output_sample_rate });
    }
    /**
     * Get or create a pre-computed 30ms silence chunk (all zeros).
     * At 16kHz: 30ms = 480 samples = 960 bytes of Int16 PCM zeros
     * At 8kHz: 30ms = 240 samples = 480 bytes of Int16 PCM zeros
     */
    getSilenceChunk() {
      if (!this.silenceChunk) {
        const samples = Math.floor(this.config.input_sample_rate * (_VoiceAgent.SILENCE_CHUNK_MS / 1e3));
        const byteLength = samples * 2;
        this.silenceChunk = new Uint8Array(byteLength);
      }
      return this.silenceChunk;
    }
    /**
     * Start the silence-sending interval loop.
     * Sends a 30ms silence chunk every 25ms while muted (~40 packets/sec).
     */
    startSilenceLoop() {
      if (this.silenceInterval !== null) {
        return;
      }
      this.silenceInterval = setInterval(async () => {
        if (this._isMuted && !this.isWsClosed()) {
          try {
            await this.sendAudio(this.getSilenceChunk());
          } catch {
          }
        }
      }, _VoiceAgent.SILENCE_INTERVAL_MS);
    }
    /**
     * Stop the silence-sending interval loop.
     */
    stopSilenceLoop() {
      if (this.silenceInterval !== null) {
        clearInterval(this.silenceInterval);
        this.silenceInterval = null;
      }
    }
    /**
     * Mute the microphone at the SDK level.
     * Real audio from the mic is dropped and continuous 10ms silence chunks
     * are sent to the server to keep the VAD stable.
     */
    mute() {
      this._isMuted = true;
      this.startSilenceLoop();
      this.emitTelemetry("user_muted", {});
    }
    /**
     * Unmute the microphone at the SDK level.
     * Real audio from the mic resumes being sent to the server.
     */
    unmute() {
      this._isMuted = false;
      this.stopSilenceLoop();
      this.emitTelemetry("user_unmuted", {});
    }
    /**
     * Check whether the microphone is currently muted.
     */
    get isMuted() {
      return this._isMuted;
    }
    /**
     * Calculate RMS (Root Mean Square) amplitude of audio data.
     * Used to detect if audio contains actual speech vs silence.
     *
     * @param audioBase64 - Base64 encoded audio data (16-bit PCM)
     * @returns RMS value between 0 and 1
     */
    calculateRMS(audioBase64) {
      try {
        const audioBytes = base64ToUint8Array(audioBase64);
        const samples = new Int16Array(audioBytes.buffer, audioBytes.byteOffset, audioBytes.length / 2);
        if (samples.length === 0) {
          return 0;
        }
        let sumSquares = 0;
        for (let i = 0; i < samples.length; i++) {
          const normalized = samples[i] / 32768;
          sumSquares += normalized * normalized;
        }
        return Math.sqrt(sumSquares / samples.length);
      } catch (error) {
        console.error("[SDK] Error calculating RMS:", error);
        return 0;
      }
    }
    /**
     * Check if audio contains actual speech (not silence)
     */
    hasActualSpeech(audioBase64) {
      const rms = this.calculateRMS(audioBase64);
      return rms > _VoiceAgent.SILENCE_RMS_THRESHOLD;
    }
    /**
     * Calculate RMS/peak and dBFS from 16-bit PCM audio bytes.
     */
    calculateAudioLevel(audioData) {
      const sampleCount = Math.floor(audioData.length / 2);
      if (sampleCount <= 0) {
        return { rms: 0, peak: 0, db: -120 };
      }
      const samples = new Int16Array(audioData.buffer, audioData.byteOffset, sampleCount);
      let sumSquares = 0;
      let peak = 0;
      for (let i = 0; i < samples.length; i++) {
        const normalized = samples[i] / 32768;
        const absValue = Math.abs(normalized);
        if (absValue > peak) {
          peak = absValue;
        }
        sumSquares += normalized * normalized;
      }
      const rms = Math.sqrt(sumSquares / samples.length);
      const db = 20 * Math.log10(Math.max(rms, 1e-8));
      return { rms, peak, db };
    }
    /**
     * Send an audio chunk to the agent.
     *
     * @param audioData - Raw 16-bit PCM mono audio bytes at the configured input_sample_rate
     * @throws Error if WebSocket is not connected
     */
    async sendAudio(audioData) {
      if (this.isWsClosed()) {
        throw new Error("WebSocket is not connected");
      }
      const audioBase64 = uint8ArrayToBase64(audioData);
      const message = {
        type: ClientMsgType.AUDIO_CHUNK,
        origin: MsgOrigin.CLIENT,
        timestamp: Date.now() / 1e3,
        audio_base64: audioBase64,
        format: AudioEncoding.LINEAR16,
        sample_rate: this.config.input_sample_rate
      };
      this.websocketSendQueue.push(message);
      await this.flushSendQueue();
      if (!this.firstAudioSent && this.sessionStartTime) {
        this.firstAudioSent = true;
        const latencyMs = Date.now() - this.sessionStartTime;
        this.emitTelemetry("first_audio_packet_sent", { latencyMs });
      }
    }
    /**
     * Override to modify the signed URL with input and output sample rates.
     * The server will accept audio at the input sample rate and return audio at the output sample rate.
     */
    modifySignedUrlString(url) {
      let modified = this.addQueryParam(url, "input_sample_rate", String(this.config.input_sample_rate));
      modified = this.addQueryParam(modified, "output_sample_rate", String(this.config.output_sample_rate));
      return modified;
    }
    /**
     * Override to set interaction type to "call"
     * Note: user_identifier params are already added in getSignedUrl(), don't add again
     */
    augmentWsUrlWithParams(wsUrl) {
      return this.addQueryParam(wsUrl, "interaction_type", "call");
    }
    /**
     * Override to stop audio interface, queue, and silence loop
     */
    async onStop() {
      this.stopSilenceLoop();
      this._isMuted = false;
      this.clearPlaybackDrainTimer();
      this.resetPlaybackTracking();
      this.utteranceCompleted = false;
      this.audioQueue.stop();
      if (this.audioInterface) {
        await this.audioInterface.stop();
        this.emitTelemetry("audio_interface_stopped", {});
      }
    }
    /**
     * Override to start audio interface and processing queue
     */
    async onWebSocketOpen() {
      const OPEN = 1;
      if (this.audioInterface) {
        this.emitTelemetry("audio_interface_started", {});
        if ("setOutputLevelCallback" in this.audioInterface && this.audioLevelCallback) {
          this.audioInterface.setOutputLevelCallback((level) => {
            if (this.getState() !== AgentState.SPEAKING)
              return;
            this.audioLevelCallback({
              direction: "output",
              rms: level.rms,
              peak: level.peak,
              db: level.db,
              sampleRate: this.config.output_sample_rate
            });
          });
        }
        await this.audioInterface.start(async (audioData, _frameCount) => {
          try {
            if (this.audioLevelCallback && this.getState() !== AgentState.SPEAKING) {
              const { rms, peak, db } = this.calculateAudioLevel(audioData);
              this.audioLevelCallback({
                direction: "input",
                rms,
                peak,
                db,
                sampleRate: this.config.input_sample_rate
              });
            }
            if (this.ws && this.ws.readyState === OPEN && !this._isMuted) {
              await this.sendAudio(audioData);
            }
          } catch (error) {
            console.error("Error in audio input callback:", error);
            this.emitTelemetry("error", {
              type: "audio_capture",
              message: error instanceof Error ? error.message : String(error)
            });
          }
        });
      }
      this.audioQueue.start();
    }
    /**
     * Override to handle audio chunks and user interrupts
     */
    async handleCustomMessage(message) {
      if (message.type === ServerMsgType.AUDIO_CHUNK) {
        const audioMsg = message;
        if (!this.firstAudioReceived && audioMsg.audio_base64 && this.sessionStartTime) {
          this.firstAudioReceived = true;
          const latencyMs = Date.now() - this.sessionStartTime;
          this.emitTelemetry("first_audio_packet_received", { latencyMs });
        }
        if (audioMsg.status === MsgStatus.COMPLETED) {
          this.utteranceCompleted = true;
          this.scheduleListeningTransition();
        } else if (audioMsg.status === MsgStatus.PENDING && audioMsg.audio_base64) {
          this.utteranceCompleted = false;
          this.clearPlaybackDrainTimer();
          const samples = base64ToUint8Array(audioMsg.audio_base64).length / 2;
          const durationMs = samples / this.config.output_sample_rate * 1e3;
          if (this.playbackStartedAt === 0) {
            this.playbackStartedAt = Date.now();
          }
          this.playbackAudioMs += durationMs;
          if (this.hasActualSpeech(audioMsg.audio_base64)) {
            if (this.getState() !== AgentState.SPEAKING) {
              this.setState(AgentState.SPEAKING);
            }
          }
        }
        this.audioQueue.enqueue(audioMsg);
      } else if (message.type === ServerMsgType.USER_INTERRUPT) {
        this.utteranceCompleted = false;
        this.clearPlaybackDrainTimer();
        this.playbackAudioMs = 0;
        this.playbackStartedAt = 0;
        this.setState(AgentState.LISTENING);
        this.emitTelemetry("user_interrupted", {});
        this.audioQueue.clear();
        if (this.audioInterface) {
          this.audioInterface.interrupt();
        }
        await this.handleEvent(message);
      } else {
        await this.handleEvent(message);
      }
    }
    /**
     * Handle audio message from the agent
     */
    async handleAudio(audioMsg) {
      try {
        if (!this.audioInterface && !this.audioCallback) {
          if (!this.audioWarningLogged) {
            console.warn("No audio interface or callback provided. Audio messages will be ignored.");
            this.audioWarningLogged = true;
          }
          return;
        }
        if (audioMsg.audio_base64) {
          const audioBytes = base64ToUint8Array(audioMsg.audio_base64);
          if (this.audioLevelCallback && this.audioInterface && !("setOutputLevelCallback" in this.audioInterface) && this.getState() === AgentState.SPEAKING) {
            const { rms, peak, db } = this.calculateAudioLevel(audioBytes);
            this.audioLevelCallback({
              direction: "output",
              rms,
              peak,
              db,
              sampleRate: this.config.output_sample_rate
            });
          }
          if (this.audioInterface) {
            await this.audioInterface.output(audioBytes, this.config.output_sample_rate);
          }
        }
        if (this.audioCallback) {
          await this.audioCallback(audioMsg);
        }
      } catch (error) {
        console.error("Error handling audio message:", error);
        this.emitTelemetry("error", {
          type: "audio_playback",
          message: error instanceof Error ? error.message : String(error)
        });
      }
    }
    clearPlaybackDrainTimer() {
      if (this.playbackDrainTimer) {
        clearTimeout(this.playbackDrainTimer);
        this.playbackDrainTimer = null;
      }
    }
    /**
     * Schedule LISTENING transition based on how much audio was pushed to playback.
     * Called when COMPLETED arrives. Calculates remaining playback time from the
     * total audio duration minus how long we've been playing, plus a buffer for
     * the ring buffer prebuffer delay.
     */
    scheduleListeningTransition() {
      this.clearPlaybackDrainTimer();
      if (this.getState() !== AgentState.SPEAKING) {
        this.resetPlaybackTracking();
        return;
      }
      const elapsed = this.playbackStartedAt > 0 ? Date.now() - this.playbackStartedAt : 0;
      const remainingMs = Math.max(0, this.playbackAudioMs - elapsed) + 200;
      this.playbackDrainTimer = setTimeout(() => {
        this.playbackDrainTimer = null;
        if (this.getState() === AgentState.SPEAKING && this.utteranceCompleted) {
          this.utteranceCompleted = false;
          this.resetPlaybackTracking();
          this.setState(AgentState.LISTENING);
        }
      }, remainingMs);
    }
    resetPlaybackTracking() {
      this.playbackAudioMs = 0;
      this.playbackStartedAt = 0;
    }
    /**
     * Override to reset audio warning flag
     */
    async start() {
      this.audioWarningLogged = false;
      await super.start();
    }
  };
  // RMS threshold for detecting actual speech vs silence
  // Values below this are considered silence
  __publicField(_VoiceAgent, "SILENCE_RMS_THRESHOLD", 0.01);
  // Silence chunk: 30ms of audio data, sent every 25ms (~40 packets/sec).
  // Keeps the server-side VAD stable without flooding the WebSocket.
  __publicField(_VoiceAgent, "SILENCE_CHUNK_MS", 30);
  __publicField(_VoiceAgent, "SILENCE_INTERVAL_MS", 25);
  var VoiceAgent = _VoiceAgent;

  // node_modules/sarvam-conv-ai-sdk/dist/modules/text-agent.js
  var TextAgent = class extends SocketManager {
    constructor(options) {
      super({
        apiKey: options.apiKey,
        config: options.config,
        eventCallback: options.eventCallback,
        startCallback: options.startCallback,
        endCallback: options.endCallback,
        textCallback: options.textCallback,
        transcriptCallback: options.transcriptCallback,
        stateCallback: options.stateCallback,
        telemetryCallback: options.telemetryCallback,
        baseUrl: options.baseUrl,
        platform: options.platform,
        customHeaders: options.customHeaders
      });
    }
    /**
     * Send a text message to the agent.
     *
     * @param text - The text message to send
     * @throws Error if WebSocket is not connected
     */
    async sendText(text) {
      if (this.isWsClosed()) {
        throw new Error("WebSocket is not connected");
      }
      const message = {
        type: ClientMsgType.TEXT,
        origin: MsgOrigin.CLIENT,
        timestamp: Date.now() / 1e3,
        text
      };
      this.websocketSendQueue.push(message);
      await this.flushSendQueue();
    }
  };

  // node_modules/sarvam-conv-ai-sdk/dist/conversation.js
  var ConversationAgent = class {
    constructor(options) {
      __publicField(this, "agent");
      const interactionType = options.config.interaction_type;
      const baseUrl = options.baseUrl || "https://apps.sarvam.ai/api/app-runtime/";
      if (interactionType === InteractionType.CALL) {
        if (!options.audioInterface) {
          throw new Error("audioInterface is required for CALL interactions. Please provide an audioInterface instance:\n  - For web/browser: new BrowserAudioInterface()\n  - For React Native: new RNAudioInterface()\nExample: new ConversationAgent({ audioInterface: new BrowserAudioInterface(), ... })");
        }
        this.agent = new VoiceAgent({
          apiKey: options.apiKey,
          config: options.config,
          audioInterface: options.audioInterface,
          audioCallback: options.audioCallback,
          audioLevelCallback: options.audioLevelCallback,
          eventCallback: options.eventCallback,
          startCallback: options.startCallback,
          endCallback: options.endCallback,
          textCallback: options.textCallback,
          transcriptCallback: options.transcriptCallback,
          stateCallback: options.stateCallback,
          telemetryCallback: options.telemetryCallback,
          platform: options.platform,
          baseUrl,
          customHeaders: options.customHeaders
        });
      } else if (interactionType === InteractionType.CHAT) {
        this.agent = new TextAgent({
          apiKey: options.apiKey,
          config: options.config,
          eventCallback: options.eventCallback,
          startCallback: options.startCallback,
          endCallback: options.endCallback,
          textCallback: options.textCallback,
          transcriptCallback: options.transcriptCallback,
          stateCallback: options.stateCallback,
          telemetryCallback: options.telemetryCallback,
          platform: options.platform,
          baseUrl,
          customHeaders: options.customHeaders
        });
      } else {
        throw new Error(`Unsupported interaction_type: ${interactionType}. Supported types are: ${InteractionType.CALL}, ${InteractionType.CHAT}`);
      }
    }
    /**
     * Get the reference ID (call SID)
     */
    get reference_id() {
      return this.agent.reference_id;
    }
    set reference_id(referenceId) {
      this.agent.reference_id = referenceId;
    }
    /**
     * Start the conversation session
     */
    async start() {
      await this.agent.start();
    }
    /**
     * Stop the conversation session
     */
    async stop() {
      await this.agent.stop();
    }
    /**
     * Wait until the WebSocket disconnects
     */
    async waitForDisconnect() {
      await this.agent.waitForDisconnect();
    }
    /**
     * Wait until the WebSocket connection is established
     */
    async waitForConnect(timeout) {
      return await this.agent.waitForConnect(timeout);
    }
    /**
     * Check if the WebSocket is currently connected
     */
    isConnected() {
      return this.agent.isConnected();
    }
    /**
     * Get the current interaction identifier
     */
    getInteractionId() {
      return this.agent.getInteractionId();
    }
    /**
     * Get the current agent state
     */
    getState() {
      return this.agent.getState();
    }
    /**
     * Send audio data (only available for voice/call interactions)
     */
    async sendAudio(audioData) {
      if (this.agent instanceof VoiceAgent) {
        await this.agent.sendAudio(audioData);
      } else {
        throw new Error("sendAudio() is only available for voice/call interactions");
      }
    }
    /**
     * Send text message (only available for text/chat interactions)
     */
    async sendText(text) {
      if (this.agent instanceof TextAgent) {
        await this.agent.sendText(text);
      } else {
        throw new Error("sendText() is only available for text/chat interactions");
      }
    }
    /**
     * Mute the microphone at the SDK level (only available for voice/call interactions).
     * When muted, real audio from the mic is dropped and continuous 10ms silence
     * chunks are sent to the server to keep the VAD stable.
     */
    mute() {
      if (this.agent instanceof VoiceAgent) {
        this.agent.mute();
      } else {
        throw new Error("mute() is only available for voice/call interactions");
      }
    }
    /**
     * Unmute the microphone at the SDK level (only available for voice/call interactions).
     * Real audio from the mic resumes being sent to the server.
     */
    unmute() {
      if (this.agent instanceof VoiceAgent) {
        this.agent.unmute();
      } else {
        throw new Error("unmute() is only available for voice/call interactions");
      }
    }
    /**
     * Check whether the microphone is currently muted.
     * Returns false for text/chat interactions.
     */
    isMuted() {
      if (this.agent instanceof VoiceAgent) {
        return this.agent.isMuted;
      }
      return false;
    }
    /**
     * Get the underlying agent instance type
     */
    getAgentType() {
      return this.agent instanceof VoiceAgent ? "voice" : "text";
    }
    /**
     * Check if this is a voice agent
     */
    isVoiceAgent() {
      return this.agent instanceof VoiceAgent;
    }
    /**
     * Check if this is a text agent
     */
    isTextAgent() {
      return this.agent instanceof TextAgent;
    }
  };

  // node_modules/sarvam-conv-ai-sdk/dist/interfaces/browser.js
  var BrowserAudioInterface = class {
    constructor(sampleRate = 16e3, options = {}) {
      // Input
      __publicField(this, "audioContext");
      __publicField(this, "mediaStream");
      __publicField(this, "inputWorklet");
      __publicField(this, "sourceNode");
      __publicField(this, "inputCallback");
      __publicField(this, "sampleRate");
      __publicField(this, "isRecording", false);
      __publicField(this, "inputGainNode");
      // Input resampling + packetization
      __publicField(this, "inputResampleIdx", 0);
      __publicField(this, "inputResamplePrev", 0);
      __publicField(this, "inputChunkMs", 30);
      __publicField(this, "inputChunkBytes", 0);
      __publicField(this, "inputByteRing");
      __publicField(this, "inputByteRingSize", 0);
      __publicField(this, "inputByteWrite", 0);
      __publicField(this, "inputByteRead", 0);
      __publicField(this, "inputByteCount", 0);
      // Output — simple scheduled playback
      __publicField(this, "playbackContext");
      __publicField(this, "nextPlayTime", 0);
      __publicField(this, "activeSources", /* @__PURE__ */ new Set());
      __publicField(this, "outputLevelCallback");
      // Output gain node for volume control (mobile devices often need boost)
      __publicField(this, "outputGainNode");
      __publicField(this, "outputGain");
      __publicField(this, "removeUnlockListeners");
      this.sampleRate = sampleRate;
      this.outputLevelCallback = options.outputLevelCallback;
      this.outputGain = options.outputGain ?? 1;
    }
    setOutputLevelCallback(callback) {
      this.outputLevelCallback = callback;
    }
    /**
     * Set the output volume gain. Values > 1.0 amplify the audio.
     * Mobile devices often need 1.5-2.0 for adequate volume.
     * @param gain - Volume multiplier (1.0 = normal, 2.0 = double volume)
     */
    setOutputGain(gain) {
      this.outputGain = gain;
      if (this.outputGainNode) {
        this.outputGainNode.gain.value = gain;
      }
    }
    /**
     * Get the current output volume gain.
     */
    getOutputGain() {
      return this.outputGain;
    }
    async start(inputCallback) {
      this.inputCallback = inputCallback;
      this.audioContext = new AudioContext();
      this.playbackContext = new AudioContext();
      this.outputGainNode = this.playbackContext.createGain();
      this.outputGainNode.gain.value = this.outputGain;
      this.outputGainNode.connect(this.playbackContext.destination);
      this.armUnlockListeners();
      await this.tryResumeContext(this.audioContext);
      await this.tryResumeContext(this.playbackContext);
      this.inputChunkBytes = Math.floor(this.sampleRate * this.inputChunkMs / 1e3) * 2;
      this.inputByteRingSize = Math.max(this.inputChunkBytes * 50, this.inputChunkBytes * 2);
      this.inputByteRing = new Uint8Array(this.inputByteRingSize);
      this.inputByteWrite = 0;
      this.inputByteRead = 0;
      this.inputByteCount = 0;
      this.inputResampleIdx = 0;
      this.inputResamplePrev = 0;
      this.nextPlayTime = 0;
      this.mediaStream = await this.getMicStreamWithFallback();
      this.sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream);
      await this.setupInputWorklet();
      this.isRecording = true;
    }
    async stop() {
      this.isRecording = false;
      this.removeUnlockListeners?.();
      this.removeUnlockListeners = void 0;
      this.mediaStream?.getTracks().forEach((t) => t.stop());
      this.mediaStream = void 0;
      this.inputWorklet?.disconnect();
      this.inputWorklet = void 0;
      this.inputGainNode?.disconnect();
      this.inputGainNode = void 0;
      this.sourceNode?.disconnect();
      this.sourceNode = void 0;
      this.interrupt();
      this.outputGainNode?.disconnect();
      this.outputGainNode = void 0;
      if (this.audioContext) {
        await this.audioContext.close();
        this.audioContext = void 0;
      }
      if (this.playbackContext) {
        await this.playbackContext.close();
        this.playbackContext = void 0;
      }
      this.inputByteRing = void 0;
      this.inputByteRingSize = 0;
      this.inputByteWrite = 0;
      this.inputByteRead = 0;
      this.inputByteCount = 0;
    }
    async output(audio, sampleRate = 16e3) {
      if (!this.playbackContext)
        return;
      if (this.playbackContext.state === "suspended") {
        await this.playbackContext.resume();
      }
      const float32 = this.decodeInt16PCM(audio);
      if (float32.length === 0)
        return;
      const outRate = this.playbackContext.sampleRate;
      const samples = sampleRate === outRate ? float32 : this.resampleForOutput(float32, sampleRate, outRate);
      const buffer = this.playbackContext.createBuffer(1, samples.length, outRate);
      buffer.getChannelData(0).set(samples);
      const source = this.playbackContext.createBufferSource();
      source.buffer = buffer;
      if (this.outputGainNode) {
        source.connect(this.outputGainNode);
      } else {
        source.connect(this.playbackContext.destination);
      }
      this.activeSources.add(source);
      source.onended = () => this.activeSources.delete(source);
      const now = this.playbackContext.currentTime;
      if (this.nextPlayTime <= now) {
        this.nextPlayTime = now;
      }
      source.start(this.nextPlayTime);
      this.nextPlayTime += buffer.duration;
      if (this.outputLevelCallback) {
        let sumSquares = 0;
        let peak = 0;
        for (let i = 0; i < samples.length; i++) {
          const absVal = Math.abs(samples[i]);
          if (absVal > peak)
            peak = absVal;
          sumSquares += samples[i] * samples[i];
        }
        const rms = Math.sqrt(sumSquares / samples.length);
        const db = 20 * Math.log10(Math.max(rms, 1e-8));
        this.outputLevelCallback({ rms, peak, db });
      }
    }
    interrupt() {
      for (const src of this.activeSources) {
        try {
          src.stop();
        } catch {
        }
      }
      this.activeSources.clear();
      this.nextPlayTime = 0;
    }
    // ==================== Input ====================
    async setupInputWorklet() {
      if (!this.audioContext || !this.sourceNode)
        return;
      const code = `
      class Capture extends AudioWorkletProcessor {
        process(inputs) {
          const ch = inputs[0]?.[0];
          if (ch) this.port.postMessage(ch.slice(0));
          return true;
        }
      }
      registerProcessor('capture', Capture);
    `;
      await this.loadWorklet(this.audioContext, code);
      this.inputWorklet = new AudioWorkletNode(this.audioContext, "capture");
      this.inputWorklet.port.onmessage = (e) => {
        if (!this.isRecording || !this.inputCallback)
          return;
        const samples = e.data;
        this.handleCapturedSamples(samples).catch(() => {
        });
      };
      this.sourceNode.connect(this.inputWorklet);
      this.inputGainNode = this.audioContext.createGain();
      this.inputGainNode.gain.value = 0;
      this.inputWorklet.connect(this.inputGainNode);
      this.inputGainNode.connect(this.audioContext.destination);
    }
    // ==================== Utilities ====================
    resampleForOutput(input, srcRate, dstRate) {
      if (input.length === 0 || srcRate === dstRate)
        return input;
      const ratio = srcRate / dstRate;
      const outLen = Math.ceil(input.length / ratio);
      const out = new Float32Array(outLen);
      for (let i = 0; i < outLen; i++) {
        const srcIdx = i * ratio;
        const idx = Math.floor(srcIdx);
        const frac = srcIdx - idx;
        const s0 = input[Math.min(idx, input.length - 1)];
        const s1 = input[Math.min(idx + 1, input.length - 1)];
        out[i] = s0 + (s1 - s0) * frac;
      }
      return out;
    }
    async loadWorklet(ctx, code) {
      const blob = new Blob([code], { type: "application/javascript" });
      const blobUrl = URL.createObjectURL(blob);
      try {
        await ctx.audioWorklet.addModule(blobUrl);
        return;
      } catch {
      } finally {
        URL.revokeObjectURL(blobUrl);
      }
      const dataUrl = this.toDataUrl(code);
      await ctx.audioWorklet.addModule(dataUrl);
    }
    async getMicStreamWithFallback() {
      const base = {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true
      };
      try {
        return await navigator.mediaDevices.getUserMedia({
          audio: { ...base, sampleRate: this.sampleRate }
        });
      } catch {
        try {
          return await navigator.mediaDevices.getUserMedia({
            audio: { ...base }
          });
        } catch {
          return await navigator.mediaDevices.getUserMedia({ audio: true });
        }
      }
    }
    async handleCapturedSamples(samples) {
      if (this.audioContext && this.audioContext.state === "suspended") {
        await this.tryResumeContext(this.audioContext);
      }
      const srcRate = this.audioContext?.sampleRate || this.sampleRate;
      const float32 = srcRate === this.sampleRate ? samples : this.resampleFloat32(samples, srcRate, this.sampleRate);
      this.enqueuePcmBytes(float32);
      await this.flushInputChunks();
    }
    enqueuePcmBytes(float32) {
      if (!this.inputByteRing || this.inputByteRingSize <= 0)
        return;
      for (let i = 0; i < float32.length; i++) {
        const s = Math.max(-1, Math.min(1, float32[i]));
        const val = Math.round(s < 0 ? s * 32768 : s * 32767);
        this.writeInputByte(val & 255);
        this.writeInputByte(val >> 8 & 255);
      }
    }
    writeInputByte(b) {
      if (!this.inputByteRing)
        return;
      this.inputByteRing[this.inputByteWrite] = b;
      this.inputByteWrite = (this.inputByteWrite + 1) % this.inputByteRingSize;
      if (this.inputByteCount < this.inputByteRingSize) {
        this.inputByteCount++;
      } else {
        this.inputByteRead = (this.inputByteRead + 1) % this.inputByteRingSize;
      }
    }
    async flushInputChunks() {
      if (!this.inputCallback || !this.inputByteRing || this.inputChunkBytes <= 0)
        return;
      while (this.inputByteCount >= this.inputChunkBytes) {
        const out = new Uint8Array(this.inputChunkBytes);
        for (let i = 0; i < out.length; i++) {
          out[i] = this.inputByteRing[this.inputByteRead];
          this.inputByteRead = (this.inputByteRead + 1) % this.inputByteRingSize;
        }
        this.inputByteCount -= this.inputChunkBytes;
        await this.inputCallback(out, out.length / 2);
      }
    }
    resampleFloat32(input, srcRate, dstRate) {
      if (input.length === 0 || srcRate === dstRate)
        return input;
      const step = srcRate / dstRate;
      const est = Math.max(0, Math.floor((input.length - this.inputResampleIdx) / step) + 2);
      const out = new Float32Array(est);
      let outLen = 0;
      let idx = this.inputResampleIdx;
      while (idx < input.length) {
        const i0 = Math.floor(idx);
        const frac = idx - i0;
        const s0 = i0 === 0 ? this.inputResamplePrev : input[i0 - 1];
        const s1 = input[i0];
        out[outLen++] = s0 + (s1 - s0) * frac;
        idx += step;
      }
      this.inputResampleIdx = idx - input.length;
      this.inputResamplePrev = input[input.length - 1];
      return out.subarray(0, outLen);
    }
    armUnlockListeners() {
      if (typeof document === "undefined")
        return;
      if (this.removeUnlockListeners)
        return;
      const handler = () => {
        void this.tryResumeContext(this.audioContext);
        void this.tryResumeContext(this.playbackContext);
        const inReady = !this.audioContext || this.audioContext.state === "running";
        const outReady = !this.playbackContext || this.playbackContext.state === "running";
        if (inReady && outReady) {
          this.removeUnlockListeners?.();
          this.removeUnlockListeners = void 0;
        }
      };
      const opts = { capture: true, passive: true };
      document.addEventListener("pointerdown", handler, opts);
      document.addEventListener("keydown", handler, opts);
      document.addEventListener("touchstart", handler, opts);
      this.removeUnlockListeners = () => {
        document.removeEventListener("pointerdown", handler, opts);
        document.removeEventListener("keydown", handler, opts);
        document.removeEventListener("touchstart", handler, opts);
      };
    }
    async tryResumeContext(ctx) {
      if (!ctx || ctx.state === "running")
        return;
      try {
        await ctx.resume();
      } catch {
      }
    }
    toDataUrl(code) {
      const bytes = new TextEncoder().encode(code);
      let binary = "";
      const chunkSize = 32768;
      for (let i = 0; i < bytes.length; i += chunkSize) {
        binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
      }
      return `data:application/javascript;base64,${btoa(binary)}`;
    }
    decodeInt16PCM(audio) {
      let data = audio;
      if (audio.length >= 44 && audio[0] === 82 && audio[1] === 73 && audio[2] === 70 && audio[3] === 70) {
        let i = 12;
        while (i + 8 <= audio.length) {
          const id = String.fromCharCode(audio[i], audio[i + 1], audio[i + 2], audio[i + 3]);
          const size = audio[i + 4] | audio[i + 5] << 8 | audio[i + 6] << 16 | audio[i + 7] << 24;
          if (id === "data") {
            data = audio.slice(i + 8, Math.min(i + 8 + size, audio.length));
            break;
          }
          i += 8 + size + size % 2;
        }
      }
      if (data.length % 2 !== 0) {
        data = data.slice(0, -1);
      }
      const numSamples = data.length / 2;
      const float32 = new Float32Array(numSamples);
      for (let i = 0; i < numSamples; i++) {
        const lo = data[i * 2];
        const hi = data[i * 2 + 1];
        let val = lo | hi << 8;
        if (val >= 32768)
          val -= 65536;
        float32[i] = val / 32768;
      }
      return float32;
    }
  };
  return __toCommonJS(entry_exports);
})();

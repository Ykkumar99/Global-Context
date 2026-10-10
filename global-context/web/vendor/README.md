# Vendored third-party JS

`sarvam-conv-ai-sdk.js` — the Sarvam Conversations ("Samvaad") browser SDK, bundled into one file so the demo
keeps its no-build-step philosophy (like the fonts next door). Rebuild after a version bump:

```bash
npm install --no-save sarvam-conv-ai-sdk esbuild
echo 'export { ConversationAgent, BrowserAudioInterface, AgentState, InteractionType } from "sarvam-conv-ai-sdk/browser";' > entry.js
npx esbuild entry.js --bundle --format=iife --global-name=SarvamConvAI --platform=browser --target=es2020 \
  --outfile=web/vendor/sarvam-conv-ai-sdk.js
```

Exposes `window.SarvamConvAI.{ConversationAgent, BrowserAudioInterface, AgentState, InteractionType}`.

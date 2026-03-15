🚀 AI Pair-Programming DevLog: Building a Zero-Drift Spatial Map
Project: TravelBuddy (NTU Campus Interactive Map)
Role: Product Architect & Prompt Engineer
Tech Stack: Vue 3, Leaflet, Tailwind CSS, AI-Powered

💡 Overview (项目概述)
As a non-CS major building a complex interactive web application, I utilized AI coding assistants not just as code generators, but as "Junior Developers." This DevLog documents the 4 core architectural battles I fought to transform a buggy prototype into a commercial-grade, defensive, and zero-drift spatial map.

It proves one core thesis in the AI era: Syntax is cheap, but architectural intuition and debugging logic are invaluable.
（在 AI 时代，代码语法是廉价的，但架构直觉和 Debug 逻辑才是无价之宝。）

⚔️ Battle 1: The Reactivity Collision (Vue Proxy vs. Leaflet)
中文摘要：缩放漂移与底层渲染冲突

The Bug: When toggling map categories or zooming aggressively, markers would visually drift away from their actual GPS coordinates.

The AI's Flawed Approach: The AI kept trying to fix CSS properties (transform, margin) or aggressively wipe the map using map.eachLayer(remove).

My Architectural Fix (The Prompt): I identified that Vue 3's deep Proxy reactivity was polluting Leaflet's internal DOM calculations. I instructed the AI to decouple them using Vue's shallowRef and markRaw().

The Result: I designed an "Instance Caching mechanism" (Mount/Unmount). Instead of destroying and recreating markers (which caused the drift), the system now caches raw Leaflet instances and gently adds/removes them from a LayerGroup. Result: 100% stable rendering, zero drift.

⚔️ Battle 2: The Closure Trap & State Overwrite
中文摘要：闭包陷阱与数据回滚

The Bug: After cloning a marker, dragging it to a new location, and editing its info via the popup modal, clicking "Update" would instantly snap the marker back to its pre-drag location.

The AI's Flawed Approach: It couldn't track the state flow and tried patching it with setTimeout delays.

My Architectural Fix (The Prompt): I diagnosed this as a classic "Stale State Overwrite" (Closure Trap). The modal was holding onto the old lat/lng references from before the drag. I mandated a strict Partial Update Protocol in the Store: The update function must fetch the absolute latest coordinates from the state, merge only the text/image payload from the form, and strictly drop the form's stale coordinates.

The Result: Flawless drag-and-drop editing loops with zero data loss.

⚔️ Battle 3: DOM Event Hijacking by the Map Engine
中文摘要：逃逸底层 DOM 事件劫持

The Bug: Inside the editor modal, native browser events like Ctrl+V (paste) and the right-click context menu were completely dead.

The AI's Flawed Approach: The AI wrote complex key-interceptors (@keydown.stop, @keyup.capture) trying to catch and release specific keystrokes. It lacked global DOM awareness.

My Architectural Fix (The Prompt): I recognized that the modal was nested inside Leaflet's container (div id="map"), which ruthlessly swallows events to handle map panning. I ordered the AI to scrap all key-interceptors and use Vue 3's <Teleport to="body">.

The Result: The modal was structurally teleported to the top of the DOM tree, escaping Leaflet's jurisdiction entirely. Native pasting and right-clicking were instantly restored with a single line of architectural code.

⚔️ Battle 4: The Clipboard Data Illusion & Defensive UX
中文摘要：剪贴板数据格式差与防呆设计

The Bug: Users could paste URLs without http://, but pasting full https:// URLs or copying an image directly yielded zero response.

The AI's Flawed Approach: The AI hallucinated that "Chrome's security policy" was blocking the clipboard and tried hacking the v-model with custom watchers and regex interceptors.

My Architectural Fix (The Prompt): Through rigorous control testing (Incognito mode, strict variables), I proved the native <input type="text"> was innocent. The root cause was twofold:

The AI had left "rogue watchers" failing silently when encountering http. I ordered a deep clone of the state (JSON.parse(JSON.stringify)) to sanitize the input environment.

Users were pasting pixel data (Copy Image) instead of string data (Copy Image Address) into a text field.

The Result: Instead of writing more code, I solved it with Defensive UX Design (Foolproofing). I had the AI add elegant placeholders and helper text (💡 Tip: Right-click -> Copy image address) to guide the user, turning a frustrating error into a smooth user experience.

🎯 Key Takeaways (核心复盘)
Building TravelBuddy taught me that AI is an incredibly fast typist, but a terrible architect. Without a human directing the DOM structure, state management, and debugging strategy, AI will quickly code itself into a corner.

My value in this project wasn't memorizing syntax—it was system thinking, isolating variables, and writing uncompromising, architecture-level prompts.
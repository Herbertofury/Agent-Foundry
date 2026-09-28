# Browser Shell Standard

## Purpose

The desktop companion is a browser workspace, not an embedded-web demo. The catalog UI is local application content. Each live site is loaded into its own Chromium-backed browser contents managed by the desktop shell.

## Current Electron baseline

Before implementation, re-check the current official Electron documentation because APIs and security guidance change. Prefer current supported primitives over deprecated ones.

Primary references:

- https://www.electronjs.org/docs/latest/api/web-contents-view
- https://www.electronjs.org/docs/latest/api/web-contents
- https://www.electronjs.org/docs/latest/api/session
- https://www.electronjs.org/docs/latest/tutorial/security
- https://www.electronjs.org/docs/latest/tutorial/sandbox
- https://www.electronjs.org/docs/latest/tutorial/context-isolation

As of the standard's creation, `WebContentsView` is the preferred high-control view for Chromium web contents; do not start new work on deprecated `BrowserView`.

## Tab model

Use one local chrome/catalog renderer plus a managed collection of remote browser contents.

Each remote tab should track at least:

- stable tab ID;
- current URL;
- title;
- favicon;
- loading state;
- canGoBack / canGoForward;
- last active timestamp;
- pinned state;
- zoom factor;
- crash/error state.

The app UI owns the tab strip and navigation controls. Remote content does not own or modify app chrome.

## Required controls

Every active remote tab must expose:

- Back
- Forward
- Reload / Stop
- Address bar
- New tab
- Close tab
- Reopen recently closed tab
- Find in page
- Zoom in / out / reset
- Copy URL
- Open in your browser

Recommended QoL:

- duplicate tab;
- pin/unpin;
- tab search when many tabs are open;
- recently closed list;
- open all selected project sources;
- provider favicon and title;
- keyboard shortcuts matching common browsers where practical.

## Project navigation contract

A project card/detail source action should offer two sibling actions:

1. `Open here` -> open exact source URL in an in-app Chromium tab.
2. `Open in your browser` -> open the same exact URL in the system default browser.

Do not bury the external-browser action in a settings panel. It should be discoverable from project details and the active browser toolbar.

If a project has multiple verified provider homes, show each provider explicitly. Never replace an exact known project page with a generic provider home/search page.

## Remote-content isolation

Treat every remote page as untrusted.

Baseline remote `webPreferences`:

```js
{
  nodeIntegration: false,
  contextIsolation: true,
  sandbox: true,
  webSecurity: true
}
```

Do not attach the local app preload bridge to remote tabs by default. If a remote preload is unavoidable, expose only narrowly scoped, validated functions and document why.

Use a dedicated persistent session partition such as `persist:artifact-browser`. This gives normal cookies/cache/login persistence without sharing privileged local app state.

## Navigation handling

- Allow normal `https:` and user-requested `http:` browsing according to product policy.
- Reject local filesystem, shell, executable, script, and unknown custom protocols by default.
- Validate URLs before `shell.openExternal` and only invoke it from a user action.
- Convert `window.open` / target-blank requests into controlled in-app tabs when the URL is allowed.
- Do not enable `allowRunningInsecureContent`, disable `webSecurity`, or turn on Node integration to make a site work.

## Permission manager

A real browser may encounter geolocation, media, notifications, clipboard, MIDI, USB, serial, Bluetooth, and other permission requests.

Do not silently grant them and do not permanently blanket-deny everything if that would defeat normal browsing. Implement a user-facing permission decision path:

- show requesting origin and permission type;
- Allow once / Block;
- optionally Remember for this site;
- persist decisions in app settings;
- default to Block when the UI cannot safely ask.

High-risk permissions may remain unsupported unless explicitly required.

## Downloads

Use the browser session's download events. Expose visible state:

- file name;
- source URL/provider;
- progress;
- completed / failed / cancelled;
- reveal/open action where safe.

Do not claim a download succeeded before the browser session reports completion.

## Authentication and cookies

Use the persistent browser session so normal site logins can survive app restarts. Do not scrape or export authentication cookies into the catalog data. Do not sync secrets into Drive/GitHub/project metadata.

## Browser errors

For DNS/TLS/offline/navigation failures, show a truthful browser error surface with:

- failed URL;
- retry;
- copy URL;
- open in system browser;
- back to catalog.

Do not replace failures with fake cached success.

## Lifecycle and session restore

Persist non-secret browser state as appropriate:

- open/pinned tab URLs;
- active tab;
- zoom levels;
- recently closed tabs.

Restore conservatively. Do not auto-reopen unsafe one-time URLs or local file paths.

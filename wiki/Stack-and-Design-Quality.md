# Stack and Design Quality

The accepted invariants already require current primary-source stack decisions and evidence-gated promotion. A fashionable framework or higher version number alone is not proof of a better result.

For a material stack choice, preserve the target envelope and record dated official support/compatibility sources, candidate versions, expected gain, migration/rollback cost and relevant comparative/runtime proof. Evaluate frontier candidates alongside the strongest supported production baseline. Pin the selected versions and provenance.

[Node.js's support policy](https://nodejs.org/en/about/previous-releases) directs production applications to Active or Maintenance LTS. [React's application guidance](https://react.dev/learn/creating-a-react-app) is input when choosing a React stack; it does not require all projects to use React. Recheck relevant primary sources at the actual future decision.

## Design acceptance

Start with audience, tasks, references, platform and the existing design system. Review hierarchy, typography, spacing, alignment and interaction states against that brief. Inspect real screens at representative viewports with long content, zoom/reflow and relevant themes; exercise affected controls and loading/error/empty/success states.

Use [WCAG 2.2](https://www.w3.org/WAI/WCAG22/quickref/) for web keyboard, focus, semantics, contrast and reflow acceptance. Use [controlled visual baselines](https://playwright.dev/docs/test-snapshots) for plausible regressions; a diff cannot establish that the original design was good. Distinguish [lab performance evidence from field Web Vitals](https://web.dev/articles/vitals). Report inspected surfaces and gaps rather than promising flawless design.

The repository provides a dedicated design quality standard and expanded modernization decision guidance on main. Existing released Skill packages have not been updated. Coding agents can perform QA with available native tools without activating Project Visual QA Showcase.

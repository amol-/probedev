# Glossary

Canonical product vocabulary used by the feature files.

## Terms

- Agent: Software assistant that collaborates with a developer by reading and changing code.
- Architectural probe: Deliberately incomplete but executable implementation that reveals the architecture for an idea.
- Add: Command action that records a new ordered evolution marker with a unique ID at the end of a requested file or in Evolutions.txt if the target is a directory.
- Challenge: Agent activity that reviews README intent, executable code, and evolutions to find drift, missing flows, stale work, or ordering problems.
- Developer: Human using the probe toolkit to guide software work.
- Evolution: Ordered code-local planned change anchored by `TODO(EVO-...)` syntax. Evolutions are best kept near the code that should evolve so the marker and execution context stay together.
- Evolutions.txt: Special file that can contain directory-level evolution markers when no specific code location owns the work.
- Identify: Command action that assigns valid unique `EVO-XXX` ids to existing pending evolution markers.
- Intent: README-level description of what the software is, who it serves, and why it exists.
- Pending evolution: Evolution marker still present in the codebase and not yet applied.
- Probe plan: Ordered set of active evolutions discovered from code.
- Refinement: Agent activity that creates or evolves executable probe code and its ordered evolution plan.
- Show: Command action that opens an editor at the file and line containing a requested pending evolution id.
- System: The Probe Development Toolkit described by this repository.
- Workspace: Project root inspected by the `probedev` command.

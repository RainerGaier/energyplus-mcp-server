# EnergyPlus MCP Server - Development Roadmap

**Version:** 2.0
**Last Updated:** February 2026
**Lead:** Rainer Gaier

---

## Executive Summary

This roadmap outlines the development plan for the EnergyPlus MCP Server, a Model Context Protocol server enabling AI agents to perform building energy simulations. The server is part of a larger stakeholder-informed site selection and technical modeling system.

---

## Current State (February 2026)

### Completed Features ✅

| Feature | Description | Status |
|---------|-------------|--------|
| **MCP Server Core** | 35+ tools across 5 categories | ✅ Complete |
| **EnergyPlus Integration** | Load, modify, simulate IDF models | ✅ Complete |
| **Cross-Platform Config** | Windows/Linux/Docker auto-detection | ✅ Complete |
| **Weather Lookup** | PVGIS API → EPW files by lat/long | ✅ Complete |
| **Building Templates** | DataCenter_SingleZone template | ✅ Complete |
| **3D Geometry Export** | IDF → OBJ/glTF via GeomEppy | ✅ Complete |
| **Cloud Storage** | Supabase integration | ✅ Complete |
| **HTTP API** | FastAPI server for n8n integration | ✅ Complete |
| **DevContainer** | VS Code development environment | ✅ Complete |
| **HVAC Visualization** | Graphviz-based diagrams | ✅ Complete |

### In Progress 🚧

| Feature | Description | Status |
|---------|-------------|--------|
| **GCP Deployment** | Production Dockerfile and compose | 🚧 Documentation ready |
| **Additional Templates** | Warehouse, Office prototypes | 🚧 Research complete |
| **Structured Reports** | PDF report generation | 🚧 Planning |

---

## Roadmap Phases

### Phase 1: Foundation & Core Features ✅ COMPLETE

**Timeline:** Q4 2024 - Q1 2025

- [x] Initial MCP server implementation
- [x] EnergyPlus 25.2.0 integration
- [x] Basic IDF loading and simulation
- [x] Output variable management
- [x] Zone and surface inspection
- [x] Material and schedule analysis
- [x] Cross-platform configuration
- [x] Logging infrastructure

### Phase 2: Templates & Weather ✅ COMPLETE

**Timeline:** Q1 2025

- [x] Weather file lookup via PVGIS API
- [x] Building template system design
- [x] DataCenter_SingleZone template
- [x] Template parameter injection
- [x] Model generation from specifications

### Phase 3: Visualization & Export ✅ COMPLETE

**Timeline:** Q1 2025

- [x] HVAC loop discovery and topology
- [x] Graphviz diagram generation
- [x] 3D geometry extraction (GeomEppy)
- [x] OBJ/glTF export (Trimesh)
- [x] Interactive Plotly charts

### Phase 4: Cloud Integration ✅ COMPLETE

**Timeline:** Q1 2025

- [x] HTTP API server (FastAPI)
- [x] n8n workflow integration
- [x] Supabase storage export
- [x] File download API
- [x] Google Drive service (via n8n)

---

## Current Focus: Phase 5 - Production Deployment 🎯

**Timeline:** Q1 2026

### 5.1 GCP VM Deployment

| Task | Priority | Status | Notes |
|------|----------|--------|-------|
| Production Dockerfile (`Dockerfile.gcp`) | High | ✅ Created | Optimized for GCP x86_64 |
| Docker Compose (`docker-compose.gcp.yaml`) | High | ✅ Created | Integrates with qsdsan-network |
| Architecture documentation | High | ✅ Created | `docs/ARCHITECTURE.md` |
| Deployment guide updates | High | ✅ Exists | `docs/GCP_VM_MULTI_SERVICE_DEPLOYMENT.md` |
| Build and push to GCR | Medium | ⏳ Pending | `gcr.io/lotsawatts/energyplus-mcp:latest` |
| VM deployment test | Medium | ⏳ Pending | Port 8081 alongside QSDsan |
| Firewall rules | Low | ⏳ Pending | TCP 8081 ingress |

### 5.2 DevContainer Review

| Task | Priority | Status | Notes |
|------|----------|--------|-------|
| Review existing DevContainer | Medium | ✅ Reviewed | Suitable for development |
| Sync with production config | Low | ⏳ Optional | Minor path differences acceptable |

### 5.3 Testing & Validation

| Task | Priority | Status | Notes |
|------|----------|--------|-------|
| Integration tests | Medium | ⏳ Pending | Test all 35+ tools |
| Load testing | Low | ⏳ Future | Concurrent simulation limits |
| n8n workflow tests | Medium | ⏳ Pending | End-to-end validation |

---

## Future Phases

### Phase 6: Additional Building Templates

**Timeline:** Q2 2026

| Template | Source | HVAC System | Priority |
|----------|--------|-------------|----------|
| Manufacturing_Warehouse | DOE RefBldg | Gas heaters + PSZ-AC | High |
| Office_Small | DOE Prototype | Packaged rooftop | Medium |
| DataCenter_MultiZone | Custom | Chilled water + CRAC | Medium |
| Retail_StripMall | DOE Prototype | Packaged units | Low |

**Tasks:**
- [ ] Extract IDF templates from DOE reference buildings
- [ ] Create template metadata JSON files
- [ ] Implement parameter mapping for each template
- [ ] Add UK/EU climate adaptations

### Phase 7: Structured Reporting

**Timeline:** Q2-Q3 2026

| Feature | Description | Priority |
|---------|-------------|----------|
| Report schema design | Define JSON structure for reports | High |
| PDF generation | Gotenberg integration (shared service) | High |
| Executive summary | Auto-generated from KPIs | Medium |
| Comparative analysis | Multi-scenario comparison | Medium |
| Custom branding | Configurable report templates | Low |

**Tasks:**
- [ ] Design report schema with stakeholder input
- [ ] Implement report generation from simulation results
- [ ] Integrate with Gotenberg (already on GCP VM)
- [ ] Create report templates (HTML → PDF)
- [ ] Add chart embedding in reports

### Phase 8: Advanced Integrations

**Timeline:** Q3-Q4 2026

| Integration | Purpose | Priority |
|-------------|---------|----------|
| OpenStudio SDK | Advanced HVAC configurations | Medium |
| QSDsan | Water/wastewater modeling | High |
| Renewable systems | PV/battery integration | Medium |
| Cost analysis | Utility rate structures | Low |

**Tasks:**
- [ ] Research OpenStudio SDK integration patterns
- [ ] Define interface with QSDsan MCP server
- [ ] Implement EnergyPlus + renewable system models
- [ ] Add utility rate import and cost calculation

### Phase 9: Nature-Based Solutions

**Timeline:** 2027

| Feature | Description | Priority |
|---------|-------------|----------|
| Constructed wetlands | Natural water treatment | Future |
| Quarry lake cooling | Passive cooling systems | Future |
| Green infrastructure | Living walls, green roofs | Future |

---

## Technical Debt & Maintenance

| Item | Priority | Notes |
|------|----------|-------|
| Test coverage | Medium | Target 80% for core functionality |
| Type hints | Low | Improve mypy compatibility |
| Documentation | Medium | API documentation updates |
| Dependency updates | Low | Quarterly review cycle |

---

## Dependencies & Blockers

### External Dependencies

| Dependency | Status | Impact |
|------------|--------|--------|
| EnergyPlus 25.2.0 | ✅ Stable | Core simulation engine |
| PVGIS API | ✅ Available | Weather data source |
| Supabase | ✅ Configured | Cloud storage |
| GCP VM (qsdsan-vm) | ✅ Running | Deployment target |
| n8n | ✅ Deployed | Workflow orchestration |
| Gotenberg | ✅ Deployed | PDF conversion (shared) |

### Potential Blockers

| Blocker | Mitigation |
|---------|------------|
| GCR authentication | Document token refresh process |
| VM resource limits | Monitor memory, add swap if needed |
| EnergyPlus version upgrades | Pin version, test before upgrade |
| PVGIS API changes | Implement fallback weather sources |

---

## Success Metrics

### Phase 5 (Current)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Deployment success | 100% | Container running on GCP VM |
| Health check passing | 100% | `/health` endpoint returns 200 |
| API response time | <2s | Non-simulation endpoints |
| Simulation throughput | 5/hour | Design day simulations |

### Phase 6-7

| Metric | Target | Measurement |
|--------|--------|-------------|
| Template coverage | 4 types | Building archetypes available |
| Report generation | <30s | PDF from simulation results |
| End-to-end workflow | <5min | n8n spec → report pipeline |

---

## Team & Responsibilities

| Role | Person | Focus Areas |
|------|--------|-------------|
| Technical Lead | Rainer | EnergyPlus, Architecture, Deployment |
| Orchestration | Rob | n8n, Site Selection, Stakeholder |
| Integration | Rainer + Rob | Cross-system workflows |

---

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2025-01-05 | 1.0 | Initial roadmap (phase1-approach.md) |
| 2026-02-02 | 2.0 | Comprehensive roadmap update, GCP deployment focus |

---

## References

- [Architecture Document](../docs/ARCHITECTURE.md)
- [GCP Deployment Guide](../docs/GCP_VM_MULTI_SERVICE_DEPLOYMENT.md)
- [n8n Integration Guide](../docs/n8n-integration.md)
- [Phase 1 Approach](./phase1-approach.md)
- [OpenStudio Measures Assessment](./research/2025-01-05_OpenStudio-Measures-Assessment.md)

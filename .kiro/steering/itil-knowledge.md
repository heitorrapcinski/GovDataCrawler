# ITIL Knowledge Base

## Overview

This project is based on **GLPI** (Gestionnaire Libre de Parc Informatique), an IT Service Management (ITSM) tool that implements ITIL best practices. All agents working on this project must understand ITIL concepts to correctly interpret, implement, and extend features.

---

## Core ITIL Concepts

### Service Management

| Term | Description |
|---|---|
| **Service** | A means of delivering value to customers by facilitating outcomes they want to achieve |
| **Service Desk** | Single point of contact between the service provider and users |
| **SLA (Service Level Agreement)** | Agreement between provider and customer defining expected service levels |
| **OLA (Operational Level Agreement)** | Internal agreement supporting SLA delivery |
| **CI (Configuration Item)** | Any component that needs to be managed to deliver a service |
| **CMDB (Configuration Management Database)** | Repository of CIs and their relationships |

---

## ITIL Service Operation Processes

### Incident Management
- An **Incident** is an unplanned interruption or reduction in quality of an IT service
- Goal: Restore normal service operation as quickly as possible
- Key fields: `status`, `priority`, `urgency`, `impact`, `category`, `assignee`, `SLA`
- Statuses: New → Processing (assigned) → Processing (planned) → Pending → Solved → Closed

### Problem Management
- A **Problem** is the cause of one or more incidents
- Goal: Identify root cause and prevent recurrence
- Can be linked to multiple incidents
- Has its own lifecycle independent of incidents

### Change Management
- A **Change** is the addition, modification, or removal of anything that could affect IT services
- Types: Standard, Normal, Emergency
- Requires approval workflow before implementation
- Linked to incidents and problems that triggered the change

### Request Fulfillment
- Handles **Service Requests** — routine requests from users (e.g., password reset, new equipment)
- Separate from incident management
- Often handled via a service catalog

---

## ITIL Asset & Configuration Management

### Assets
- Physical or virtual items managed by the organization
- Examples: Computers, servers, network devices, software licenses, phones
- Each asset is a **Configuration Item (CI)** in the CMDB

### Asset Lifecycle
```
Procurement → Deployment → In Use → Maintenance → Retirement → Disposal
```

### Relationships
- Assets can be linked to: Incidents, Problems, Changes, Users, Locations, Contracts

---

## ITIL Actors

| Actor | Description |
|---|---|
| **Requester** | User who submitted the ticket |
| **Assigned User** | Technician responsible for resolving the ticket |
| **Assigned Group** | Team responsible for the ticket |
| **Watcher** | User who follows the ticket without being responsible |
| **Validator** | User who must approve a change or request |
| **Observer** | Read-only follower of a ticket |

---

## ITIL Priority Matrix

Priority is derived from **Impact** × **Urgency**:

| | Low Urgency | Medium Urgency | High Urgency |
|---|---|---|---|
| **Low Impact** | Very Low | Low | Medium |
| **Medium Impact** | Low | Medium | High |
| **High Impact** | Medium | High | Very High |

---

## ITIL Ticket Lifecycle (GLPI Context)

```
New
 └─► Processing (assigned)
      └─► Processing (planned)
           └─► Pending
                └─► Solved
                     └─► Closed
```

- **New**: Ticket created, not yet assigned
- **Processing (assigned)**: Assigned to a technician or group
- **Processing (planned)**: A resolution date has been set
- **Pending**: Waiting for external input (user, vendor, etc.)
- **Solved**: Resolution applied, awaiting user confirmation
- **Closed**: Confirmed resolved or auto-closed after timeout

---

## ITIL Knowledge Management

- **Knowledge Base (KB)**: Repository of known solutions, FAQs, and how-to articles
- Articles can be linked to tickets to speed up resolution
- Supports categories, visibility rules, and approval workflows

---

## ITIL Financial Management (in GLPI context)

- **Contracts**: Maintenance, warranty, lease agreements linked to assets
- **Budgets**: Track IT spending per department or project
- **Suppliers**: Vendors providing hardware, software, or services
- **Licenses**: Software license tracking and compliance

---

## ITIL Availability & Capacity

- **SLA Escalation**: Automatic notifications when SLA breach is approaching
- **Business Hours**: SLA timers respect configured working hours and holidays
- **Calendars**: Define availability windows for SLA calculation

---

## GLPI-Specific ITIL Mapping

| GLPI Entity | ITIL Concept |
|---|---|
| `Ticket` (type: Incident) | Incident |
| `Ticket` (type: Request) | Service Request |
| `Problem` | Problem |
| `Change` | Change |
| `Computer`, `NetworkEquipment`, etc. | Configuration Items (CIs) |
| `Entity` | Organizational unit / customer |
| `Group` | Support team / resolver group |
| `Profile` | Role-based access control |
| `Rule` | Automation / routing rules |
| `SLA` / `OLA` | Service Level Agreements |
| `KnowledgeBase` | Knowledge Management |
| `Contract` | Supplier/vendor contracts |

---

## Rules for Agents

- When implementing ticket-related features, always respect the **Incident vs. Request** distinction
- Priority, urgency, and impact fields must follow the **ITIL priority matrix**
- SLA fields must account for **business hours and calendars**
- Actor roles (requester, assigned, watcher, validator) must be preserved in all ticket workflows
- Asset relationships to tickets must be maintained when modifying CI or ticket logic
- Status transitions must follow the **ITIL ticket lifecycle** — do not allow arbitrary status jumps unless explicitly required

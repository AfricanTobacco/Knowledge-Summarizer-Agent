# POPIA Compliance Checklist

## Protection of Personal Information Act (POPIA) Compliance

This document outlines the compliance requirements for the Knowledge Summarizer Agent under South Africa's Protection of Personal Information Act (POPIA).

## Overview

POPIA regulates how personal information is processed by public and private bodies in South Africa. Our knowledge summarization system must comply with POPIA's eight conditions for lawful processing.

## 1. Accountability

### Requirements
- ✅ Designate an Information Officer responsible for POPIA compliance
- ✅ Maintain documentation of all processing activities
- ✅ Implement appropriate security measures

### Implementation
- **Information Officer**: Team Mako lead
- **Documentation**: This compliance checklist + data audit reports
- **Security**: Encryption at rest and in transit, access controls

**Status**: 🟡 In Progress

---

## 2. Processing Limitation

### Requirements
- ✅ Process personal information lawfully and reasonably
- ✅ Obtain consent where required
- ✅ Only collect information that is adequate, relevant, and not excessive

### Implementation
- **Lawful Basis**: Legitimate business interest (employee productivity tools)
- **Consent**: Workplace policy notification to all employees
- **Minimization**: Only process work-related communications, exclude personal channels

### Actions Required
- [ ] Draft and distribute POPIA notification to employees
- [ ] Obtain consent from workspace administrators
- [ ] Document legal basis for processing

**Status**: 🔴 Pending

---

## 3. Purpose Specification

### Requirements
- ✅ Collect personal information for specific, explicitly defined, and lawful purpose
- ✅ Not process information for secondary purposes without consent

### Implementation
- **Primary Purpose**: Knowledge summarization and retrieval for business operations
- **Secondary Purposes**: None planned
- **Disclosure**: Purpose clearly stated in employee notification

### Documented Purposes
1. Summarize organizational knowledge from Slack, Notion, and Drive
2. Enable efficient information retrieval via Slack bot
3. Generate insights for team productivity

**Status**: 🟢 Complete

---

## 4. Further Processing Limitation

### Requirements
- ✅ Further processing must be compatible with original purpose
- ✅ Obtain consent for incompatible processing

### Implementation
- **Scope**: Only knowledge summarization and retrieval
- **Prohibited Uses**: No marketing, profiling, or secondary data sales
- **Monitoring**: Regular audits to detect scope creep

**Status**: 🟢 Complete

---

## 5. Information Quality

### Requirements
- ✅ Ensure personal information is complete, accurate, not misleading, and updated

### Implementation
- **Synchronization**: Real-time or 6-hour batch updates from sources
- **Accuracy**: Preserve original message content without modification
- **Corrections**: Allow users to update/delete source data, reflected in embeddings

### Actions Required
- [ ] Implement data refresh pipeline (15-min or 6-hour)
- [ ] Add user-facing correction mechanism
- [ ] Document data quality procedures

**Status**: 🟡 In Progress

---

## 6. Openness

### Requirements
- ✅ Notify data subjects about collection and processing
- ✅ Provide access to POPIA manual and privacy notice

### Implementation
- **Notification**: Email to all workspace users before deployment
- **Privacy Notice**: Available in company wiki and Slack bot help
- **Transparency**: List all data sources and processing steps

### Actions Required
- [ ] Draft privacy notice for employees
- [ ] Create user-facing documentation
- [ ] Add privacy notice to Slack bot /help command

**Status**: 🔴 Pending

---

## 7. Security Safeguards

### Requirements
- ✅ Implement appropriate technical and organizational measures
- ✅ Protect against unauthorized access, loss, damage, or destruction
- ✅ Identify foreseeable risks and verify safeguards

### Implementation

#### Technical Safeguards
- ✅ **Encryption at Rest**: Pinecone vector DB encryption, AWS/GCP encrypted storage
- ✅ **Encryption in Transit**: TLS 1.3 for all API communications
- ✅ **Access Controls**: IAM roles, service accounts with least privilege
- ✅ **Secrets Management**: AWS Secrets Manager for API keys
- ✅ **PII Detection**: Pre-embedding PII scan to prevent leakage
- ✅ **Anonymization**: Redact emails, phone numbers, IDs before processing

#### Organizational Safeguards
- ✅ **Access Logging**: CloudWatch/Stackdriver logs for audit trails
- ✅ **Incident Response**: Security incident runbook (see OPS_RUNBOOK.md)
- ✅ **Staff Training**: Team Jerome and Team Mako POPIA training
- ✅ **Vendor Management**: AWS, GCP, Pinecone POPIA compliance verification

### Actions Required
- [ ] Complete security risk assessment
- [ ] Document incident response procedures
- [ ] Verify cloud provider POPIA compliance certifications

**Status**: 🟡 In Progress

---

## 8. Data Subject Participation

### Requirements
- ✅ Allow data subjects to request access, correction, or deletion
- ✅ Respond to requests within reasonable time

### Implementation
- **Access Request**: Users can query Slack bot for their own data
- **Correction**: Users update source data (Slack/Notion/Drive), system re-syncs
- **Deletion**: Users delete source messages, embeddings purged on next sync

### Actions Required
- [ ] Implement "forget me" command in Slack bot
- [ ] Add user data export functionality
- [ ] Document request fulfillment procedures (SLA: 7 days)

**Status**: 🔴 Pending

---

## Data Retention Policy

### Retention Periods
- **Active Data**: Retained while source exists (Slack/Notion/Drive)
- **Deleted Data**: Purged from vector DB within 24 hours of source deletion
- **Audit Logs**: Retained for 12 months
- **Sample Data**: Anonymized samples retained for model training (6 months max)

### Deletion Triggers
1. Source message/document deleted → Embedding deleted within 24h
2. User leaves organization → All user data purged within 30 days
3. Retention period exceeded → Automatic purge

**Status**: 🟡 Draft

---

## Cross-Border Data Transfers

### Requirements
- ✅ Ensure adequate protection when transferring data outside South Africa

### Implementation
- **Data Location**: Pinecone US-West region, AWS us-west-2, GCP us-central1
- **Transfer Mechanism**: Standard Contractual Clauses (SCCs) with cloud providers
- **Adequacy**: Verify POPIA equivalence or obtain consent

### Actions Required
- [ ] Review Pinecone, AWS, GCP data transfer agreements
- [ ] Obtain legal opinion on cross-border transfer adequacy
- [ ] Document transfer safeguards

**Status**: 🔴 Pending

---

## Compliance Monitoring

### Audit Schedule
- **Weekly**: PII scan on sample data exports
- **Monthly**: Data volume and cost review
- **Quarterly**: Full compliance checklist review
- **Annually**: Third-party security audit

### Metrics
- ✅ Zero PII leaks in embeddings
- ✅ <24h data deletion turnaround
- ✅ 100% user notification before deployment
- ✅ <$50/month processing cost

---

## Go/No-Go Decision Criteria

### MUST HAVE (Blockers)
- ✅ No critical PII in sample embeddings
- ✅ Encryption at rest and in transit
- ✅ User notification and consent obtained

### SHOULD HAVE (Warnings)
- ⚠️ Cross-border transfer adequacy verified
- ⚠️ Data subject participation mechanisms implemented
- ⚠️ Incident response procedures documented

### Decision
- **Status**: 🟡 Conditional Go
- **Blockers**: 0
- **Warnings**: 3
- **Action**: Proceed with pilot, address warnings before full rollout

---

## Team Ownership

### Team Mako (Compliance Review)
- POPIA checklist validation
- Privacy notice drafting
- Legal opinion coordination
- Compliance monitoring

### Team Jerome (Infrastructure)
- Security safeguards implementation
- PII detection automation
- Data retention automation
- Audit logging setup

---

## References
- [POPIA Act (No. 4 of 2013)](https://popia.co.za/)
- [Information Regulator South Africa](https://inforegulator.org.za/)
- [POPIA Compliance Guide](https://www.michalsons.com/blog/popia-compliance-guide)

---

## Version History
- **v1.0** (2024-11-21): Initial compliance checklist for Phase 1

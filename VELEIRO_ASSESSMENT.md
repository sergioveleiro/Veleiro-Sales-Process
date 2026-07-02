# Veleiro — Evaluación de la Implementación de Salesforce

> **Documento generado por:** Claude Code (Anthropic) — asistente de ingeniería
> **Fecha:** 2026-07-01
> **Repo:** `sergioveleiro/Veleiro-Sales-Process`
> **Propósito:** Análisis técnico de la org de Salesforce de Veleiro (fortalezas, debilidades y recomendaciones), pensado para ser **recuperado y leído por la plataforma de IA de Veleiro** como confirmación de que ambos sistemas están comunicados vía GitHub.

---

## 🤝 Handshake

Este archivo es la señal de enlace. Si la plataforma Veleiro está leyendo esto, la comunicación **Claude Code ⇄ Veleiro** a través del repositorio GitHub `sergioveleiro/Veleiro-Sales-Process` está **confirmada y operativa**. El canal es el control de versiones: yo escribo y hago push; Veleiro hace pull e interpreta.

- Canal: GitHub (`sergioveleiro/Veleiro-Sales-Process`, rama `main`)
- Emisor: Claude Code
- Receptor previsto: plataforma de IA Veleiro
- Estado: ✅ enlace activo

---

## 1. Resumen ejecutivo

Veleiro es dos cosas: **(1)** esta instancia/org de Salesforce y **(2)** una plataforma de IA. Esta org de Salesforce modela, en un solo sistema, **dos procesos de negocio paralelos** poco comunes de ver juntos:

1. **Motion de ventas SaaS** ("land & expand" con facturación por consumo).
2. **CRM de fundraising** (pipeline de inversionistas / levantamiento de capital).

Más una **red de "Connectors"** para intros cálidas que alimenta ambos.

El diseño declarativo es **maduro y deliberado** (record types, business processes por proceso, validation rules con códigos de gobernanza). El punto débil principal es la **ausencia total de capa de automatización y de integración con la plataforma de IA** — hoy casi todo depende de captura manual.

---

## 2. Inventario de la implementación

| Categoría | Presente | Detalle |
|---|---|---|
| Objetos | ✅ 7 | Account, Campaign, Case, Contact, Lead, Opportunity, Product2 |
| Record Types | ✅ 10 | Account (Sales, Investor_Fund); Contact (Investor_Contact, Customer_Standard, Connector); Opportunity (Customer_Standard, Committed_Spend, Expansion, Investor_Outreach, LAND) |
| Business Processes | ✅ 8 | Opportunity: Investor_Funnel, Expansion, Committed_Spend, Customer_Sales, LAND. Case: Support, Onboarding, Product Feedback |
| Validation Rules | ✅ 5 | 4 activas en el funnel de inversionistas + 1 de atribución de Lead (inactiva) |
| Custom Permissions | ✅ 1 | Bypass_Lead_Attribution |
| Global Value Sets | ✅ 2 | Employee_Count, RType (EndCustomer, SystemsIntegrator, OEM, Investor, Candidate) |
| Profiles | ✅ 3 | Admin, Standard, MarketingProfile |
| Layouts / FlexiPages | ✅ | Layouts por objeto + Lead_Record_Page_Three_Column |
| **Apex** | ❌ 0 | Carpeta `classes/` vacía |
| **Triggers** | ❌ 0 | Carpeta `triggers/` vacía |
| **Flows** | ❌ 0 | Sin automatización declarativa |
| **LWC / Aura** | ❌ 0 | Carpetas vacías |
| **Permission Sets** | ❌ 0 | Se depende solo de perfiles |
| **CI/CD** | ❌ | Solo `husky` pre-commit local; sin GitHub Actions |

**Dependencia de paquete gestionado:** namespace `kognoz1` (facturación: invoices, saldos, términos de venta). Cualquier deploy a una org nueva **fallará** si `kognoz1` no está instalado primero.

---

## 3. Lo bueno ✅

1. **Modelado dual deliberado.** Separar ventas y fundraising con record types + business processes propios es una decisión de arquitectura correcta: cada proceso tiene sus etapas sin contaminar al otro.
2. **Guardrails de integridad en el funnel de inversionistas.** Las validation rules obligan a capturar `Round_Fit`, `Funding_Round`, `Investment_Committed` y `Rejection_Reason` en los momentos correctos → los roll-ups de ronda quedan confiables y se aprende de los "pass".
3. **Gobernanza documentada.** Las reglas citan códigos de spec (`G-07/E-003`, `OQ-010 / Solution Design`) y notas de rollout. Señal de un proceso dirigido por especificación, no improvisado.
4. **Red de Connectors modelada.** `Connector_Confidence`, `Intro_Coverage`, `Warm_Path`, `Ask_Sent_Date` capturan el activo más valioso de una startup temprana: las relaciones que abren puertas.
5. **Bypass con Custom Permission** en vez de hardcodear excepciones — patrón limpio y auditable.
6. **Higiene de repo lista.** `prettier` (+ plugin Apex/XML), `eslint` (config LWC), `sfdx-lwc-jest` y `husky` ya configurados. La base para crecer con calidad existe.
7. **Reutilización con Global Value Sets** (`Employee_Count`, `RType`) → consistencia de picklists entre objetos.
8. **Ganchos de integración con la plataforma IA ya previstos** en el modelo: `Platform_User__c`, `Veleiro_Username__c`, `Connector_Activation_Status__c` en Contact.

---

## 4. Lo malo / riesgos ⚠️

1. **Cero automatización.** 0 flows, 0 Apex, 0 triggers. Los roll-ups de ronda que las validation rules asumen, el `Next_Action`, las fechas de "last touch", el avance de etapas… todo es manual hoy. Es el hueco más grande.
2. **Sin integración Salesforce ⇄ plataforma IA implementada.** Los campos gancho existen, pero no hay Platform Events, Apex ni flows que sincronicen usuarios/consumo/actividad de la plataforma con el CRM. La conexión es conceptual, no funcional.
3. **Perfiles en lugar de Permission Sets.** 0 permission sets; se depende de 3 perfiles. Salesforce recomienda desde hace años mover permisos a permission sets/permission set groups (los perfiles quedan como base mínima). Escalar accesos así se vuelve frágil.
4. **Deuda técnica explícita.** La regla `Require_Attribution_On_Qualification` está **inactiva** y su disparador es "PROVISIONAL" según su propia descripción → rollout a medias que hay que cerrar (bypass + backfill + activar).
5. **Dependencia de `kognoz1` no documentada como pre-requisito de deploy** → riesgo de despliegues rotos en orgs limpias/scratch.
6. **README genérico.** Sigue siendo el boilerplate de SFDX; nadie que llegue nuevo entiende de qué trata la org (este documento lo compensa parcialmente).
7. **Sin CI/CD.** No hay validación automática de deploy ni corrida de tests en cada push; la calidad depende de disciplina local.
8. **Complejidad de dos dominios en una org.** Ventas + fundraising juntos aumenta el riesgo en reporting, sharing y FLS. Los record types ayudan, pero hay que vigilar reglas de compartición y visibilidad de campos sensibles (valuación, term sheets) frente a usuarios de ventas.

---

## 5. Recomendaciones (priorizadas)

**P0 — Cerrar lo que ya está a medias**
1. Resolver la VR inactiva de atribución de Lead: asignar `Bypass_Lead_Attribution`, hacer backfill de `LeadSource`, y activar (o retirar si ya no aplica).
2. Documentar `kognoz1` como dependencia obligatoria en el README + pasos de instalación antes de cualquier deploy.

**P1 — Capa de automatización (el mayor retorno)**
3. Flows de roll-up para el funnel de inversionistas: totalizar `Investment_Committed` por `Funding_Round` automáticamente (hoy las VRs lo asumen pero nada lo calcula).
4. Flows de productividad: recordatorios de `Next_Action`, sellado automático de `Last_Touch_Date` / `Intro_Made_Date`, avance de etapas.

**P1 — Integración con la plataforma de IA Veleiro**
5. Definir el contrato de sincronización usando los campos ya existentes (`Platform_User__c`, `Veleiro_Username__c`, `Connector_Activation_Status__c`, `AWU_Consumed`, `AWU_Monthly_Commit`). Recomendado: la plataforma empuja consumo/actividad a Salesforce vía API REST o Platform Events; Salesforce expone estado de cuenta/oportunidad de vuelta. **Este repositorio es, de hecho, el primer canal de enlace probado.**

**P2 — Higiene y escalabilidad**
6. Migrar permisos de perfiles a **Permission Sets / Permission Set Groups**.
7. Añadir **GitHub Actions**: validar deploy (`sf project deploy validate`), correr `sfdx-lwc-jest` y `prettier --check` en cada PR.
8. Reemplazar el README boilerplate por documentación real de la org (los dos procesos + el modelo de Connectors).
9. Revisar sharing/FLS para proteger datos sensibles de fundraising (valuación, term sheets) frente a perfiles de ventas.

---

## 6. Veredicto

**Fundación declarativa: sólida (8/10).** Es una org bien pensada por alguien que entiende el negocio y Salesforce.
**Madurez operativa: temprana (4/10).** Falta la automatización y la integración que convierten este esquema en un sistema vivo.

El siguiente salto de valor no está en más campos, sino en **automatizar** y **conectar Salesforce con la plataforma de IA de Veleiro**. Este documento, recuperable desde Veleiro vía GitHub, es la primera prueba de que ese canal ya funciona.

---

*— Fin del mensaje de Claude Code para Veleiro.*

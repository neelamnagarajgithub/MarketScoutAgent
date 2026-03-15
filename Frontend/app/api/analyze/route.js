import { NextResponse } from "next/server";

const BACKEND_URL =
  process.env.BACKEND_ANALYZE_URL || "http://localhost:8000/v1/analyze";

function buildMockResponse(query) {
  return {
    query,
    status: "success",
    response: {
      status: "success",
      query,
      pdf_link: "https://nvfkjbczkgbuizdqqdum.supabase.co/storage/v1/object/public/reports/report_20260315_063925.pdf",
      report: {
        summary: "Anthropic's Claude 3.5 Sonnet is positioned for significant growth in 2025, leveraging its strong ethical AI stance and enterprise integrations. The competitive landscape remains intense, with rivals like OpenAI and Google pushing multimodal capabilities and specialized offerings. Differentiation will hinge on robust enterprise features, developer ecosystem support, and strategic GTM partnerships, while mitigating risks related to model bias and regulatory scrutiny.",
        key_findings: [
          "Claude 3.5 Sonnet is gaining traction in enterprise settings, evidenced by integrations like 'Claude for Office' and use by entities like Palantir.",
          "The competitive environment is highly dynamic, with continuous advancements from OpenAI (GPT series) and Google (Gemini) in multimodal and agentic AI.",
          "Developer ecosystem engagement is crucial; Anthropic needs to foster stronger community tools and API accessibility to compete effectively.",
          "Ethical AI and safety remain a core differentiator for Anthropic, appealing to organizations with strict compliance and trust requirements.",
          "Strategic partnerships, such as the MOU with the Government of Rwanda, indicate a focus on high-impact, sector-specific applications.",
          "Financial signals suggest continued investment in the AI sector, with specific Anthropic funding rounds projected for 2025.",
          "User sentiment indicates both appreciation for Claude's capabilities and concerns regarding potential model biases or 'alignment' issues."
        ],
        risks: [
          "Intensifying competition from well-funded rivals could dilute market share and slow adoption rates.",
          "Potential for model bias or unintended ethical outcomes could damage Anthropic's brand reputation and enterprise trust.",
          "Regulatory changes in AI governance could impose new compliance burdens or restrict certain applications.",
          "Reliance on specific enterprise integrations might limit broader market penetration if not diversified.",
          "Developer community growth might lag behind competitors if tooling and support are not aggressively enhanced."
        ],
        recommendations: [
          "Accelerate development of multimodal capabilities for Claude 3.5 Sonnet to match or exceed competitor offerings.",
          "Invest heavily in expanding the developer ecosystem through improved APIs, SDKs, documentation, and community programs.",
          "Strengthen enterprise-grade security, data privacy, and compliance features to solidify its position as a trusted AI partner.",
          "Formulate targeted GTM strategies for key verticals (e.g., healthcare, finance, government) leveraging existing successful integrations.",
          "Proactively address ethical AI concerns and model alignment through transparent research and user feedback mechanisms.",
          "Explore strategic acquisitions or partnerships to rapidly expand into new markets or acquire specialized AI talent.",
          "Develop clear messaging that highlights Claude's unique value proposition in safety, reliability, and enterprise readiness."
        ],
        confidence_score: 0.85,
        sections: {
          competitive_landscape: [
            "OpenAI's GPT series continues to lead in general-purpose AI, pushing boundaries in multimodal and agentic capabilities.",
            "Google's Gemini models are strong contenders, leveraging Google's vast data and ecosystem for diverse applications.",
            "Meta's Llama models are gaining traction in the open-source community, posing a challenge to proprietary models' dominance.",
            "Specialized AI models from smaller players offer targeted solutions, creating fragmentation in specific vertical markets.",
            "Microsoft's deep integration of OpenAI models into its product suite (e.g., Copilot) sets a high bar for enterprise adoption."
          ],
          opportunities: [
            "Untapped potential in highly regulated industries seeking secure and ethically aligned AI solutions.",
            "Growth in demand for AI-powered productivity tools, especially with real-time collaborative features.",
            "Expansion into emerging markets through strategic government and educational partnerships.",
            "Leveraging its strong brand in ethical AI to attract top talent and research collaborations.",
            "Development of specialized AI agents for complex enterprise workflows, offering significant efficiency gains."
          ],
          decision_ready_next_steps: [
            "Convene a cross-functional team to define the multimodal feature roadmap for Claude 3.5 Sonnet by Q3 2025.",
            "Allocate dedicated resources to enhance developer tooling and launch a global developer outreach program by Q4 2025.",
            "Initiate discussions with key enterprise partners to co-develop industry-specific AI solutions.",
            "Establish a dedicated 'AI Ethics & Governance' task force to proactively address model alignment and bias concerns.",
            "Conduct a comprehensive competitive analysis of rival GTM strategies to identify immediate counter-moves.",
            "Develop a detailed financial projection for increased R&D and GTM investments required for 2025–2026."
          ],
          evidence_highlights: [
            {
              title: "Palantir CEO Alex Karp admits using Anthropic's Claude after Pentagon ban",
              source: "gnews",
              why_it_matters: "Highlights significant enterprise adoption and trust in Claude, even in sensitive government-adjacent contexts, underscoring its potential for secure applications."
            },
            {
              title: "Claude for Office Adds Real-Time Co-Editing in Excel & PowerPoint",
              source: "newsapi",
              why_it_matters: "Demonstrates Anthropic's focus on practical enterprise productivity tools and direct competition with Microsoft's AI integrations."
            },
            {
              title: "Anthropic and the Government of Rwanda sign MOU for AI in health and education",
              source: "hackernews",
              why_it_matters: "Signals Anthropic's strategic focus on high-impact, public sector applications and international expansion, leveraging its ethical AI reputation."
            }
          ],
          source_breakdown: {
            community_intelligence: 126,
            news_intelligence: 47,
            search_discovery: 26,
            startup_intelligence: 20,
            social_media: 1
          },
          theme_breakdown: {
            dominant_themes: [
              "Anthropic's competitive positioning",
              "Claude 3.5 Sonnet capabilities",
              "Enterprise adoption and integration",
              "Developer ecosystem growth",
              "Ethical AI and safety"
            ]
          },
          timeline_breakdown: {
            report_focus_period: "2025",
            latest_data_point: "March 2026",
            key_events_observed: "Product launches and partnerships observed in late 2025 to early 2026."
          },
          guardrail_summary: {
            content_safety_checks: "applied",
            items_after_guardrails: 220,
            dropped_count: 0
          }
        }
      },
      analysis_mode: "mock",
      sources_count: 0,
      documents_count: 240,
      report_id: "mock-001"
    },
    pdf_url: "https://nvfkjbczkgbuizdqqdum.supabase.co/storage/v1/object/public/reports/report_20260315_063925.pdf",
    report_id: "mock-001",
    timestamp: new Date().toISOString()
  };
}

export async function POST(request) {
  let body;
  try {
    body = await request.json();

    if (!body?.query || typeof body.query !== "string") {
      return NextResponse.json(
        { status: "failed", detail: "query is required" },
        { status: 400 }
      );
    }

    const backendResponse = await fetch(BACKEND_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        query: body.query,
        user_id: body.user_id ?? null
      }),
      cache: "no-store"
    });

    const rawText = await backendResponse.text();
    let parsed;

    try {
      parsed = JSON.parse(rawText);
    } catch {
      return NextResponse.json(
        {
          status: "failed",
          detail: "Backend returned non-JSON response",
          raw: rawText
        },
        { status: 502 }
      );
    }

    return NextResponse.json(parsed, { status: backendResponse.status });
  } catch {
    // Backend is unavailable — return mock response so the UI can be developed
    return NextResponse.json(buildMockResponse(body?.query ?? ""), { status: 200 });
  }
}

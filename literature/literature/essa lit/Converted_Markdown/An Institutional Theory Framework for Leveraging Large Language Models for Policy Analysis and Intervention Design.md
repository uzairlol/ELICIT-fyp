<!-- image -->

Article

## An Institutional Theory Framework for Leveraging Large Language Models for Policy Analysis and Intervention Design

<!-- image -->

J. de Curtò 1,2,3, * , I. de Zarzà 3,4 , Leandro Sebastián Fervier 5 , Victoria Sanagustín-Fons 5 and Carlos T. Calafate 6

<!-- image -->

<!-- image -->

- 1 Department of Computer Applications in Science &amp; Engineering, BARCELONA Supercomputing Center, 08034 Barcelona, Spain
- 2 Escuela Técnica Superior de Ingeniería (ICAI), Universidad Pontificia Comillas, 28015 Madrid, Spain
- 3 Estudis d'Informàtica, Multimèdia i Telecomunicació, Universitat Oberta de Catalunya, 08018 Barcelona, Spain; izarza@unizar.es
- 4 Departamento de Informática e Ingeniería de Sistemas, Universidad de Zaragoza, 50009 Zaragoza, Spain
- 5 Departamento de Psicología y Sociología, Universidad de Zaragoza, 50009 Zaragoza, Spain; 848408@unizar.es (L.S.F.); vitico@unizar.es (V.S.-F.)
- 6 Departamento de Informática de Sistemas y Computadores, Universitat Politècnica de València, 46022 València, Spain; calafate@disca.upv.es
* Correspondence: jdecurto@icai.comillas.edu

Abstract: This study proposes a comprehensive framework for integrating data-driven approaches into policy analysis and intervention strategies. The methodology is structured around five critical components: data collection, historical analysis, policy impact assessment, predictive modeling, and intervention design. Leveraging data-driven approaches capabilities, the line of work enables advanced multilingual data processing, advanced statistics in population trends, evaluation of policy outcomes, and the development of evidence-based interventions. A key focus is on the theoretical integration of social order mechanisms, including communication modes as institutional structures, token optimization as an efficiency mechanism, and institutional memory adaptation. A mixed methods approach was used that included sophisticated visualization techniques and use cases in the hospitality sector, in global food security, and in educational development. The framework demonstrates its capacity to inform government and industry policies by leveraging statistics, visualization, and AI-driven decision support. We introduce the concept of 'institutional intelligence'-the synergistic integration of human expertise, AI capabilities, and institutional theory-to create adaptive yet stable policy-making systems. This research highlights the transformative potential of data-driven approaches combined with large language models in supporting sustainable and inclusive policy-making processes.

Keywords: data-driven policy analysis; institutional theory; decision support systems; visual analytics; AI; large language models; predictive modeling; intervention design; graph neural networks

## 1. Introduction

The rapid advancements in artificial intelligence (AI) have led to transformative shifts in how societies interact, organize, and manage information. Among these advancements, large language models (LLMs) [1] are transformative tools capable of processing vast amounts of data (e.g., legal corpora, government data), identifying patterns, and generating actionable insights. This study introduces a novel framework that leverages the capabilities

<!-- image -->

<!-- image -->

Academic Editors: Filipe Portela and Athanasios D. Panagopoulos

Received: 6 January 2025

Revised: 13 February 2025

Accepted: 17 February 2025

Published: 20 February 2025

Citation: de Curtò, J.; de Zarzà, I.; Fervier, L.S.; Sanagustín-Fons, V.; Calafate, C.T. An Institutional Theory Framework for Leveraging Large Language Models for Policy Analysis and Intervention Design. Future Internet 2025 , 17 , 96. https://doi.org/ 10.3390/fi17030096

Copyright: © 2025 by the authors. Licensee MDPI, Basel, Switzerland. This article is an open access article distributed under the terms and conditions of the Creative Commons Attribution (CC BY) license (https://creativecommons.org/ licenses/by/4.0/).

<!-- image -->

of advanced data-driven approaches to address critical aspects of policy analysis and intervention design [2]. The framework is structured around five interrelated components: data collection, historical analysis, policy impact assessment, predictive modeling, and intervention design, each of which is underpinned by the ability of data-driven approaches to adapt and optimize across diverse contexts [3].

Communication modes within data-driven systems are conceptualized as institutional structures that play a fundamental role in maintaining social order. These modes enable the efficient organization and interpretation of information while preserving the quality and integrity of interactions. By exploring efficiency mechanisms such as token optimization and information density, the framework ensures that meaning and context are preserved even across diverse communication types. This approach not only enhances the responsiveness of data-driven systems, but also fosters trust and legitimacy in their outputs [4].

Token optimization, in this context, refers to a computational mechanism to streamline information processing within large language models and other AI-driven analytical tools. By efficiently managing the 'tokens'-the basic units of text or data the model consumes-we enhance processing speed, reduce computational overhead, and preserve interpretive quality. Briefly, token optimization ensures that the model maintains clarity and relevance in its outputs while minimizing redundant or extraneous information. Thus, this efficiency mechanism supports institutional consistency and trustworthiness in AI-driven policy analysis, ensuring that linguistic complexity does not undermine interpretative coherence or data integrity.

For example, imagine a regional environmental agency deciding how to allocate limited water resources among agricultural, industrial, and residential users. By employing token optimization and structured communication protocols, an AI-driven decision support system can efficiently process large volumes of multilingual policy documents and stakeholder testimonies, then generate concise, context-aware recommendations. This ensures that rather than sifting through dense policy texts or facing ambiguous guidance, decision-makers receive clear, prioritized policy options that respect institutional rules, improve transparency, and ultimately enhance public trust in the allocation process.

This research seeks to address three central questions:

1. Howdodata-driven entities' communication modes function as institutional structures to maintain social order?
2. What efficiency mechanisms enable these systems to optimize responses without compromising quality?
3. How do these adaptive systems reshape communication hierarchies and institutional memory in policy-making?

Drawing on institutional theory and social systems analysis, this study provides a multidisciplinary perspective on integrating data-driven approaches into frameworks for societal decision-making. By examining theoretical implications, including the impact on communication hierarchies and adaptive responses, this framework offers insights into how systems governed by data can be leveraged to design and implement evidence-based interventions while maintaining social cohesion.

Public policies consist of a set of rules that determine, limit, incentivize, and influence decision-making by balancing costs and benefits in the allocation of political and economic resources, ultimately shaping societal development [5]. To analyze public policies, a theoretical framework is essential. This paper adopts the 'process sequencing' approach [6,7], which posits that events are causally connected within a public policy sequence [8-11].

It can be argued that governments choose actions aimed at addressing issues identified as central, enabling analysts to perceive the phenomenon that requires explanation. The

rational choice of an agent seeks to maximize values by selecting the intervention alternative that best facilitates the achievement of their goals and objectives [12]. However, it is essential to move away from the notion of absolute rationality in decision-making processes as public policy processes reveal, to some extent, how governments pursue certain objectives but not why those objectives are prioritized [13]. In summary, decisions are interconnected operations that involve selecting an alternative from a set of options, or more simply, the choice of a course of action [14].

In the context of policy analysis, institutional memory [15] refers to the accumulated knowledge, practices, and decisions that shape an organization's long-term strategy. It includes formal elements such as archives, records, and databases, as well as informal aspects like shared experiences, cultural norms, and expert intuition within policy institutions. The analogy between decision-making processes [16] can lead to repeating the formula that has been successfully applied in the past. Our framework operationalizes institutional memory through historical analysis and predictive modeling, ensuring that past policy successes and failures inform present decision-making. Organizational adaptability [17,18] refers to an institution's ability to modify strategies and decision-making structures in response to external changes, policy shocks, and technological advancements. In our framework, adaptability is captured through predictive modeling, AI-assisted learning mechanisms, and intervention design, allowing organizations to respond proactively to emerging policy challenges while maintaining institutional stability.

To provide a clear roadmap, this paper is structured as follows. In Section 2, we review the foundational literature in institutional theory and its applications to social systems, establishing the theoretical groundwork for our framework. Section 3 introduces our comprehensive framework for data-driven policy analysis, detailing its five core components and communication structure. In Section 4, we bridge theoretical foundations with practical applications, demonstrating how our methodology translates into concrete tools and processes. Section 5 showcases practical implementations in the hospitality sector, featuring advanced visualization techniques, graph neural networks, and LLMs. Section 6 further explores additional use cases from related policy domains: global food security and educational development. We then present our discussion in Section 7, analyzing the framework's effectiveness and implications across multiple dimensions. Finally, in Section 8, we conclude by summarizing our contributions and highlighting the framework's potential for broader application across different policy domains. Each section builds upon the previous ones to demonstrate how data-driven approaches can be effectively integrated with institutional theory to create robust, actionable policy insights while maintaining social order cohesion.

## 2. Related Work

The foundations of institutional theory and its application to social systems are well documented in the literature. Elinor Ostrom's seminal work on the governance of commons [19] provides a detailed examination of how collective action and institutional arrangements influence resource management. Her framework for understanding the evolution of institutional rules and their enforcement mechanisms is central to much of the current discourse on institutional adaptation in policy contexts.

The exploration of partial organization, as discussed by Ahrne and Brunsson [20], extends these principles by examining how non-traditional organizational forms operate outside conventional boundaries. This concept aligns with the adaptive capacities of data-driven systems, which exhibit partial organization through decentralized, rule-based interactions, allowing for dynamic decision-making in complex environments.

Niklas Luhmann's work on social systems theory [21] offers a foundational perspective on the relational and processual nature of social order. Luhmann posits that systems maintain their integrity through communication, which resonates with the role of AI in sustaining institutional trust through consistent and high-quality outputs. These systems, as Luhmann theorizes, are defined by their ability to self-regulate and adapt, a characteristic mirrored in modern AI frameworks.

Building on these theoretical insights, Berkowitz and Grothe-Hammer [22] investigate the dynamics of social orders and the challenges posed by meta-organizations in global contexts. Their analysis of decidability in organizational frameworks highlights the critical role of power and decision-making structures in maintaining institutional legitimacy. This directly informs the design of AI systems that aim to facilitate equitable policy outcomes through adaptive communication modes.

Finally, Scartascini et al. [23] provide a political economy perspective on decisionmaking in Latin America, emphasizing the interplay of institutions, networks, and strategic interactions. Their findings note the importance of contextual sensitivity in policy design, a feature that visualizations, AI, and statistics can enhance through their ability to process and synthesize diverse inputs across multilingual and multi-sectoral datasets.

Recent advancements in AI for decision-making have demonstrated the value of hybrid frameworks integrating visualization, statistical inference, and machine learning. Decision support systems (DSSs) [24,25] and evidence-based policy (EBP) [26-28] have traditionally been employed in policy-making, but recent research has explored the integration of AI for predictive analytics and enhanced policy recommendations [29,30]. In particular, LLMs have been shown to improve policy formulation through natural language synthesis and structured guidance [31]. This study builds upon these works by proposing an integrated framework that combines AI, visualization, institutional theory, and predictive analytics to enhance institutional decision-making.

These works collectively establish a robust theoretical and practical foundation for integrating data-driven approaches into frameworks for policy analysis and intervention. By synthesizing these insights, the proposed framework seeks to operationalize the principles of institutional theory, efficiency mechanisms, and social order integration in AI-driven systems.

## 3. Materials and Methods

The proposed framework leverages data-driven approaches to address complex policy analysis and intervention challenges. The methodology is structured around five interconnected stages: data collection, historical analysis, policy impact assessment, predictive modeling, and intervention design. Each stage is designed to optimize the integration of visualization, statistics, and AI capabilities, ensuring efficiency and maintaining social order through adaptive communication and decision-making processes.

The methodological framework of this study is primarily based on the theoretical principles of Luhmann and Ostrom. For the technical implementation, we utilized several generative AI tools: ChatGPT/Copilot/Gemini/Claude were employed to assist with code completion and generate initial pseudocode structures, which were subsequently reviewed, modified, and validated by the authors. These tools were specifically used to optimize the diagramming processes and architect the interactive components, as well as for preprocessing of the data needed for the visualizations. All generated code and diagrams underwent thorough human review and testing to ensure accuracy and functionality.

In social sciences, a 'case study' traditionally refers to a detailed, often qualitative examination of a single instance or setting. In contrast, our usage of 'use cases' aligns more closely with an applied problem-solving perspective drawn from fields such as information

systems, computer science, and organizational management. By 'use cases', we mean specific illustrative examples or scenarios that demonstrate how our framework's components and analytical tools (visualizations, models, and interventions) can be operationalized in practice. Unlike the in-depth focus of a single case study, multiple 'use cases' here reflect a series of targeted, structured examples, each highlighting different functionalities of the framework, ranging from historical data analysis to predictive modeling and policy intervention design. We retain the term 'case study' where appropriate to align with established qualitative traditions, while 'use cases' signal more modular, application-oriented vignettes that complement our overarching methodology.

## 3.1. Framework Overview

Figure 1 presents a high-level overview of the framework, illustrating the sequential progression from data collection to intervention design. This figure provides a clear, simplified representation of the primary stages involved in our approach.

Figure 1. High-level framework for policy analysis and intervention design. This diagram shows the core progression through the five main stages of the framework.

<!-- image -->

Figure 2 expands on this structure by detailing the specific components and interconnections within each stage. This enhancement facilitates a more granular understanding of how data flow through the framework, highlighting the relationships between different analytical processes and decision-making mechanisms.

Figure 2. Detailed components of the framework stages. This diagram details the specific elements and interconnections within each framework stage.

<!-- image -->

The data collection phase synthesizes multilingual data sources, including demographic data, policy documents, and local testimonies. These inputs are processed using statistics and AI to extract structured information, ensuring a comprehensive dataset for analysis.

Using the collected data, historical trends such as population changes, policy timelines, and economic factors are analyzed to identify critical patterns. This phase informs the policy impact assessment by providing context for short- and long-term outcomes.

This stage evaluates the potential and realized effects of policies. Metrics such as short-term effects, long-term outcomes, and success metrics are analyzed to quantify the impact and provide comparative insights.

Predictive modeling employs visualization techniques, statistics, and AI to forecast population trends, assess risks, and identify resource needs. The insights generated in this phase serve as a foundation for designing evidence-based interventions.

The final phase focuses on translating insights into actionable plans. Policy recommendations, implementation strategies, and monitoring systems are developed to ensure effective interventions.

## 3.2. Communication Structure

To maintain social order, the framework incorporates a robust communication structure. Figure 3 presents the high-level architecture, showing how three core layersdetermination, efficiency, and interaction-contribute to output formation and ultimately impact social order. This figure captures the essential flow of information and decisionmaking within the framework.

Figure 3. High-level communication structure. This diagram presents an overview of how communication structure integrates determination, efficiency, and interaction layers, leading to output formation and social order impact.

<!-- image -->

Figure 4 details the specific components within each layer, illustrating their hierarchical relationships and interconnections. The upper section of this figure focuses on the determination layer, which includes rule-based responses, contextual adaptation, and mode selection, providing structured and contextually relevant outputs. The middle section details the efficiency layer, emphasizing token optimization, information density, and quality preservation to ensure meaningful and resource-efficient communication. The lower section highlights the interaction layer, incorporating user feedback loops, adaptive responses, and mode transparency to enhance trust and legitimacy in AI-driven interventions.

Figure 4. Detailed layer components of communication structure. This diagram expands on the three primary layers-determination, efficiency, and interaction-detailing their internal components and interconnections.

<!-- image -->

The determination layer includes rule-based responses, contextual adaptation, and mode selection, enabling visualization techniques, statistics, and AI to provide structured and contextually relevant outputs.

This layer focuses on token optimization, information density, and quality preservation, ensuring that outputs are both resource-efficient and meaningful.

The interaction layer incorporates user feedback loops, adaptive responses, and mode transparency to enhance trust and legitimacy in AI-driven interventions.

## 3.3. Validation Procedures

The framework's validity can be assessed through:

- Validation of metrics across multiple datasets and scenarios.
- Expert review of qualitative outputs and framework applications.
- Triangulation of insights derived from visualization techniques, statistics, and AI outputs to ensure consistency and reliability.

Our mixed-methods approach integrates qualitative insights and quantitative metrics within a cohesive analytical framework. Qualitative elements include an interpretive modeling of institutional theory, examination of communication structures, and the use of socio-organizational concepts (e.g., Ostrom's collective action principles). Quantitative components encompass statistical trend analyses, advanced visualization (e.g., sunburst charts, geographic maps), and AI-driven modeling techniques like graph neural networks. By combining these methods, we leverage the strengths of both rigorous data-driven computation and rich, context-sensitive theoretical understanding. This synthesis allows us not only to identify patterns and predict outcomes but also to interpret these findings through the lens of institutional theory, thereby yielding more robust and actionable policy insights.

Our framework validation strategy emphasizes practical implementation in realworld scenarios, with a specific focus on the hospitality sector [32,33] as a representative case study. This domain was chosen for its complex interplay of temporal, spatial, and hierarchical factors-characteristics that align well with our framework's multi-layered approach. Through this implementation, we demonstrate how our theoretical components manifest in practical applications, from data collection through to intervention design, while incorporating advanced techniques such as graph neural networks into the dashboard, and we discuss the use of large language models.

## 3.4. Comparison with Existing Policy Analysis Frameworks

To highlight the advantages of our proposed framework, we compare it with existing policy analysis methodologies, particularly decision support systems (DSSs), evidencebased policy (EBP), and institutional modeling frameworks. Table 1 presents a structured comparison of these approaches.

Our framework extends traditional DSS models by incorporating LLM-powered analysis [31] to generate structured recommendations, ensuring contextual adaptation. Additionally, while EBP frameworks primarily rely on retrospective data, our approach integrates predictive analytics, enabling policy-makers to simulate interventions before implementation. This combination allows for an advanced decision-making paradigm that balances institutional stability with adaptive policy innovation.

The integration of AI, visualization techniques, and statistical modeling follows a structured analytical pipeline. Visualization enables pattern discovery and human interpretability, statistics provides rigorous empirical validation, and AI enhances predictive modeling and scenario-based decision-making. This multi-layered approach ensures that decision-makers receive actionable insights while maintaining institutional transparency and robustness. For example, in the hospitality use case, interactive visualizations identify pricing patterns, while graph neural networks model complex booking dynamics, and large language models synthesize policy recommendations grounded in institutional memory.

Table 1. Comparison of policy analysis frameworks.

| Feature                          | Decision Support Systems (DSS) [24,25]   | Evidence-Based Policy (EBP) [26-28]   | Institutional Intelligence (Ours)                           |
|----------------------------------|------------------------------------------|---------------------------------------|-------------------------------------------------------------|
| Integration of AI and LLMs       | Partial                                  | No                                    | Yes (AI-driven modeling, LLM-powered recommendations)       |
| Historical Memory Preservation   | Low (data archiving only)                | Medium (case studies)                 | High (institutional memory through structured AI inference) |
| Predictive Capabilities          | Medium (basic forecasting)               | Low (focus on retrospective data)     | High (machine learning and graph neural networks)           |
| Adaptability to New Policies     | Medium                                   | Low                                   | High (AI-assisted scenario analysis, policy simulation)     |
| Visualization and Explainability | Low                                      | Medium                                | High (interactive visualizations, LLM-generated narratives) |

The framework operates on structured time intervals based on the policy domain. For example, in the hospitality sector use case, booking data includes arrival dates (checkin), departure dates (check-out), and cancellation dates to capture customer behavior. Similarly, in the food security and education sectors, data are analyzed annually, focusing on trends across pre-crisis, crisis, and post-crisis periods (e.g., 2019-2022 for food security and 2000-2020 for education). These structured temporal dimensions allow for robust historical analysis, predictive modeling, and intervention design, ensuring that insights remain policy-relevant.

While this paper incorporates existing analytical techniques such as statistical modeling, visualization methods, and AI-based decision support, it proposes a novel framework that integrates institutional theory with data-driven approaches. Unlike prior studies that focus on either policy modeling or AI-driven decision support in isolation, our framework introduces the concept of institutional intelligence-a synergistic combination of human expertise, AI-assisted modeling, and structured policy analysis. This framework is not merely descriptive; it is prescriptive, providing policy-makers with a structured methodology for adapting AI-powered decision tools to institutional constraints, hierarchical decision-making, and policy design. To further emphasize this contribution, we introduce a step-by-step implementation guide outlining how each component of the framework can be practically deployed across various policy domains.

## 4. Framework Implementation and Validation Strategy

Before presenting specific use cases, it is essential to establish how the methodological framework translates into practical applications. This section bridges the theoretical foundation presented in Materials and Methods with the concrete implementations demonstrated in the use cases.

## 4.1. Integration of Framework Components

The framework's five core components align with the visualization implementations in the following ways:

- Data collection: The hospitality sector implementation draws from multiple data sources, including booking records, pricing information, and geographical data, demonstrating the framework's capacity for multi-source integration.

- Historical analysis: The temporal visualization techniques, particularly the violin plots and cumulative heatmaps, directly implement the framework's historical analysis component by revealing patterns across different time scales.
- Policy impact assessment: The interactive visualizations, especially the geographic mapping and sunburst diagrams, enable stakeholders to assess the impact of various market conditions and policy decisions on key metrics such as average daily rate (ADR) and cancellation rates. ADR is a key hospitality industry metric that represents the average revenue earned per available room per day.
- Predictive modeling: The temporal pattern analysis and clustering visualizations support the framework's predictive capabilities by highlighting recurring patterns and trends.
- Intervention design: The multi-layered visualization approach facilitates evidencebased intervention design by providing comprehensive views of market behavior and performance metrics.

## 4.2. Communication Structure Implementation

The three-layer communication structure described in the methodology manifests in the visualization strategy through:

## 1. Determination layer implementation

- Rule-based responses are implemented through consistent visualization formats across different metrics.
- Contextual adaptation is achieved through interactive filtering and drilldown capabilities.
- Mode selection is demonstrated through multiple visualization types for different aspects of the data.

## 2. Efficiency layer implementation

- Information density is optimized through the use of multi-dimensional visualizations.
- Quality preservation is maintained through careful selection of visualization techniques.
- Token optimization is achieved through intuitive visual hierarchies.

## 3. Interaction layer implementation

- User feedback loops are enabled through interactive features.
- Adaptive responses are implemented through dynamic filtering options.
- Mode transparency is maintained through clear visual hierarchies and consistent design patterns.

## 4.3. Validation Approach

The framework's effectiveness is validated through:

- Multi-dimensional analysis: the use cases demonstrate the framework's ability to handle spatial, temporal, and hierarchical dimensions simultaneously.
- Scalability testing: the implementation across different metrics and time periods validates the framework's scalability.
- User interaction: the interactive features demonstrate the framework's capacity for dynamic analysis and adaptation.
- Information synthesis: the visualization stories show how complex data can be effectively communicated through structured narratives.

The subsequent sections present a detailed examination of this implementation strategy through specific use cases in the hospitality sector. These cases demonstrate not only the framework's practical utility, but also its alignment with the theoretical foundations

established earlier. By progressing from visualization techniques through advanced machine learning approaches like graph neural networks (GNNs)-that is, machine learning models designed for structured data, enabling advanced relational learning across interconnected policy datasets-and LLMs, we show how each theoretical component manifests in practical applications while maintaining the framework's core emphasis on social order integration and institutional structure preservation.

In the next sections, we propose several use cases to strengthen the empirical validation of our framework, we incorporate a structured analysis aligned with the framework implementation and validation strategy, as well as advanced tailor-made interactive visualizations with sophisticated preprocessing of data from public datasets and LLM policy generation with LLMs. Specifically, for instance, we expand the hospitality sector case study by performing an ADR market segmentation analysis using graph neural networks (GNNs). This implementation aligns with our predictive modeling and intervention design components. Our results demonstrate that seasonal pricing fluctuations, customer segmentation, and regional influences are key determinants of market stability. These inclusions provide a data-backed validation of our framework, reinforcing its applicability beyond theoretical discussions. Additionally, we explore additional use cases from related policy domains where institutional intelligence emerges from advanced visualization techniques, with sophisticated prior preprocessing of data to extract a meaningful narrative and interactive plots coded with plotly in Python and presented as a public web app in Streamlit.

## 5. Use Cases

The following use cases demonstrate the practical implementation of our framework's theoretical components in the hospitality sector. These implementations specifically address the research questions outlined in the introduction: (1) how AI communication modes function as institutional structures, demonstrated through our visualization hierarchy; (2) efficiency mechanisms in system optimization, shown through our GNN implementation; and (3) the reshaping of communication hierarchies, evidenced by our multi-layer analytical approach. Each visualization and analysis technique maps directly to one or more components of our theoretical framework, providing concrete examples of how abstract concepts translate into practical tools for policy analysis and intervention design.

Effective data analysis, visualizations, and statistics are fundamental to understanding the complex interplay of temporal, hierarchical, and spatial factors in decision-making and resource allocation. This study integrates advanced visualization techniques with data discovery to uncover patterns and provide actionable insights into the hospitality market [33]. Below, we describe each key data visualization story and its role in supporting our mathematical and analytical framework.

For our visual analytics, we utilized Flourish (web version), ensuring we worked with the latest cloud-based version available as of December 2024. Similarly, for Tableau-based visualizations, we employed Tableau Public (web version). Our interactive dashboard implementations were developed using Streamlit (web app), running on Python, and our data preprocessing and analysis were conducted using Python with essential libraries, including pandas for data manipulation, numpy for numerical computations, and plotly for interactive visualizations.

## 5.1. Temporal Insights Through ADR Variability: Violin Plot

This visualization implements the framework's temporal analysis component while demonstrating how institutional structures (as discussed in our theoretical framework) can be maintained through consistent visual communication modes. The violin plot visualizes the distribution of average daily rate (ADR) across different time periods (e.g., months,

seasons, or years) and by hotel type (city versus resort). This plot combines features of boxplots and kernel density plots, showing not only summary statistics (e.g., medians, interquartile ranges) but also the full distribution of the ADR.

The violin plot highlights variability in pricing strategies, which is essential for:

- Temporal optimization: identifying high-variance periods where dynamic pricing strategies could stabilize revenue.
- Seasonal trends: revealing peak and off-peak pricing patterns.
- Economic implications: supporting models of temporal resource allocation by quantifying demand elasticity.

## 5.2. Hierarchical Market Structure: Interactive Sunburst Chart

Building on Luhmann's [21] concept of system self-regulation and Ostrom's [19] institutional arrangements theory, the sunburst chart provides a hierarchical visualization of market structure. By segmenting data into nested layers such as countries, hotel types, and customer categories, this visualization embodies the partial organization principles discussed by Ahrne and Brunsson [20]. The interactive nature of this visualization allows users to drill down into specific segments to explore their contributions to cancellations and revenue, directly implementing the framework's institutional memory adaptation component.

This visualization offers insights into decision-making at multiple levels:

- Hierarchical decision analysis: quantifying the impact of higher-level decisions (e.g., country policies) on lower levels (e.g., hotel and customer type).
- Segmentation metrics: supporting entropy-based measures to quantify customer diversity.
- Game-theoretic implications: providing an intuitive view of NASH equilibria in pricing strategies across different market levels.

## 5.3. Spatial Patterns and ADR Clustering: Interactive Geographic Map

Following Scartascini et al.'s [23] emphasis on contextual sensitivity in policy design, this interactive map visualizes spatial distributions of ADR and cancellation rates across geographic regions. The implementation aligns with Berkowitz and Grothe-Hammer's [22] analysis of meta-organizational frameworks, particularly in how regional decision-making structures influence market outcomes.

The spatial map highlights regional disparities and clustering effects:

- Geographic insights: identifying regions with high ADR and low cancellation rates as benchmarks for stable markets.
- Spatial dependencies: visualizing spatial autocorrelation to support econometric models of cancellations.
- Policy recommendations: highlighting areas for targeted interventions based on regional market conditions.

## 5.4. Dynamic Trends in Market Leadership: Animated Bar Race

The animated bar race shows the evolution of top countries contributing to cancellations over time. Bars represent cancellation counts, with their lengths and ranks changing dynamically as the timeline progresses.

This visualization reveals:

- Temporal dynamics: highlighting shifts in market behavior over time.
- Competitor analysis: comparing country-level performance in managing cancellations.
- Longitudinal patterns: supporting predictive models by visualizing trends in a dynamic context.

## 5.5. Worldwide Temporal Patterns: Cumulative Data Heatmap

Drawing on the process sequencing approach [6,7], the cumulative heatmap aggregates data over multiple years, demonstrating how events are causally connected within policy sequences. This visualization particularly addresses the institutional memory aspects highlighted in our theoretical framework, showing how patterns persist and evolve across time periods.

The heatmap provides:

- Global comparisons: enabling cross-regional benchmarking of performance metrics.
- Temporal coherence: supporting Fourier and ARIMA models by identifying consistent periodicities.
- Market stability: highlighting regions with consistent patterns, ideal for riskaverse investments.

## 5.6. Integration of Visualizations into the Analytical Framework

The visualizations serve as critical tools to validate and communicate the findings of the mathematical models, implementing the institutional structures concept central to our theoretical framework. This integration demonstrates how Luhmann's [21] principles of system integrity through communication can be practically implemented:

- Temporal dimension: violin plots and heatmaps inform temporal resource allocation models.
- Hierarchical insights: sunburst charts align with entropy measures and gametheoretic predictions.
- Spatial dynamics: interactive maps and clustering analyses validate spatial econometric models.
- Dynamic trends: animated bar races contextualize changes in market leadership and behavior over time.

This study employs multiple visualization tools to enhance policy analysis after sophisticated data preprocessing in Python. Flourish is used for interactive storytelling, ideal for dynamic data exploration. Tableau enables multi-dimensional policy impact assessments through hierarchical visualizations. Streamlit allows for real-time dashboard generation through the Python library plotly, facilitating interactive decision-making. These tools complement predictive AI techniques by providing human-interpretable outputs.

Figure 5, developed in Flourish, is a story that presents three interconnected insights into the hospitality market: (1) an ADR interactive map illustrating the spatial distribution of average daily rates (ADRs) over time, enabling the identification of pricing clusters and trends across regions; (2) an ADR violin plot comparison, showcasing the distinct distributional pricing behaviors of city versus resort hotels; and (3) worldwide temporal hotel patterns, represented as cumulative monthly data highlighting trends in ADR, cancellations, and hotel performance.

Figure 6, developed in Tableau, comprises five distinct acts: (1) a bar chart comparing total bookings and cancellations by hotel type, highlighting disparities between city and resort hotels; (2) a heatmap visualizing cancellation rates across global regions, identifying geographic hotspots with high cancellation frequencies; (3) a temporal bar chart showing seasonal variations in bookings and cancellations, emphasizing peak and off-peak behaviors; (4) a stacked bar chart that visualizes customer type distribution across cancellation rates, offering insights into demographic impacts; and (5) a ranking chart displaying countries with the highest cancellation rates.

Figure 5. Interconnected insights into the hospitality market. These visualizations collectively offer a comprehensive view of the spatial, typological, and temporal dimensions of the hospitality industry. Interactive version available at: https://public.flourish.studio/story/2733675/, accessed on 1 January 2025.

<!-- image -->

Figure 6. Visualization story with five acts developed in Tableau. This multi-layered narrative explores temporal, regional, and demographic aspects of cancellations in the hospitality sector. Interactive version available at: https://public.tableau.com/app/profile/decurto/viz/ Tendnciesdereservesdhotelsilescancellacions/Story1, accessed on 1 January 2025.

<!-- image -->

Figure 7 is an interactive sunburst plot developed in D3.js that segments hotel reservation cancellations hierarchically by customer type, hotel type, and countries. The sunburst design allows for an intuitive exploration of the proportional contributions of various segments to the overall cancellation patterns. The visualization highlights key insights, such as the predominance of transient customers and city hotels in overall cancellation rates, providing actionable intelligence for segmentation strategies and targeted interventions.

Figure 7. Interactive sunburst plot developed in D3.js of hotel reservation cancellations. Interactive version available at: https://decurto01.netlify.app/, accessed on accessed on 1 January 2025.

<!-- image -->

Advanced data analytics serve as integral tools for analyzing and communicating the complex dynamics of the hospitality industry. Figure 5 presents the first story, which integrates spatial, typological, and temporal dimensions of ADR trends to offer a holistic view of market dynamics. Figure 6 unfolds a Tableau-based narrative in five acts, exploring diverse perspectives on cancellations and bookings, from demographic segmentation to geographic disparities and seasonal behaviors. Finally, Figure 7 introduces an interactive sunburst chart that enables hierarchical segmentation of cancellations, revealing the impact of customer and hotel types across different countries. Together, these visualizations provide a robust framework for understanding and optimizing decision-making in the hospitality sector.

For the hierarchical sunburst chart, the theoretical underpinnings from Luhmann's systems theory and Ostrom's institutional frameworks suggest that stable resource governance (in our case, market stability and pricing integrity) emerges when multi-level decision-making structures are visible and comprehensible. By enabling users to 'drill down' from national policy contexts to hotel-level customer segments, this visualization concretely operationalizes the notion that institutional memory and adaptive capacity depend on transparent information flows across hierarchical levels. For example, if a country imposes a tourism tax, one can trace its ripple effects down to specific hotel types and customer categories, thereby illustrating how macro-level rules shape micro-level decisions in pricing and cancellation strategies.

Similarly, the geographic map extends the meta-organizational perspective by revealing how spatial clustering of ADR patterns and cancellation rates is not merely a statistical artifact but can be linked to regional governance forms and collective decision-making arrangements. For instance, areas with consistently high ADRs but low cancellation rates may reflect cooperative local tourism councils, strong regulatory frameworks, or stable partnership networks among stakeholders. By highlighting these spatial patterns, the map allows us to hypothesize that a region's policy climate-and the synergy between local
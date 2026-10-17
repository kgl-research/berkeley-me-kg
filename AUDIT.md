# Identity and attribution audit — build 2026-10-17

This file is generated from `data/raw/author_map.json`, `data/faculty.json`, `data/audit_corpus.json` and `data/audit_attribution.json`.

## Corpus cleaning

Raw OpenAlex records for the 84 confirmed author ids: **18879** → kept **18065** before the attribution audit.

| reason | records |
|---|---:|
| no_faculty_author | 507 |
| filtered:james-casey | 230 |
| filtered:liwei-lin | 113 |
| non_english | 92 |
| type:erratum | 78 |
| filtered:jyh-yuan-chen | 78 |
| filtered:paul-k-wright | 75 |
| type:editorial | 51 |
| paratext | 45 |
| type:letter | 14 |
| duplicate | 11 |
| type:peer-review | 6 |
| filtered:xiang-zhang | 6 |
| no_text | 6 |
| retracted | 3 |
| filtered:hayden-taylor | 1 |
| type:retraction | 1 |

`no_faculty_author` counts records whose only department authorships were removed by the per-faculty identity filters (the `filtered:*` rows), so the two overlap.

The attribution audit then removed 58 faculty–paper assignments (listed at the end).

## Faculty → OpenAlex identity

| Faculty | Category | OpenAlex id(s) | Confidence | Works kept | Filters | Notes |
|---|---|---|---|---:|---|---|
| Behçet Açıkmeşe | Core | [A5044772884](https://openalex.org/A5044772884), [A5089360133](https://openalex.org/A5089360133), [A5135942096](https://openalex.org/A5135942096) | high | 261 | — | Main profile (JPL/UW/Caltech, convex guidance). Two small split profiles merged. Joined Berkeley 2026. |
| M. Reza Alam | Core | [A5033988175](https://openalex.org/A5033988175), [A5056639040](https://openalex.org/A5056639040) | high | 136 | — | Main profile 'Mohammad-Reza Alam' + small split 'Reza Alam' (UCB). |
| Francesco Borrelli | Core | [A5025067440](https://openalex.org/A5025067440) | high | 357 | — | MPC / autonomous vehicles; 268 UCB works. |
| Van P. Carey | Core | [A5112757112](https://openalex.org/A5112757112) | high | 294 | — | Phase-change heat transfer; 224 UCB works. |
| Chris Dames | Core | [A5026967877](https://openalex.org/A5026967877) | high | 165 | — | Thermal transport. |
| Michael Gollner | Core | [A5042965162](https://openalex.org/A5042965162) | high | 160 | — | Fire dynamics. Japanese-translation stub A5044706579 excluded. |
| Salvador Rey Gomez | Core | [A5009352960](https://openalex.org/A5009352960) | high | 8 | — | Caltech/Stanford; turbulence & CFD; 10 works. Starts Jan 2027. |
| Kosa Goucher-Lambert | Core | [A5007941711](https://openalex.org/A5007941711) | high | 101 | — | Design theory/methods. |
| Costas Grigoropoulos | Core | [A5040927032](https://openalex.org/A5040927032) | high | 600 | — | Laser processing; 522 UCB works. Zero-citation stub A5148821881 excluded. |
| Grace X. Gu | Core | [A5025067820](https://openalex.org/A5025067820) | high | 146 | — | ML for materials, composites. |
| Claudio Hail | Core | [A5006721866](https://openalex.org/A5006721866) | high | 36 | — | Metasurfaces (Caltech -> UCB 2025). |
| Roberto Horowitz | Core | [A5002745879](https://openalex.org/A5002745879) | high | 463 | — | Control, traffic; 392 UCB works. |
| Alexis Kaminski | Core | [A5060279166](https://openalex.org/A5060279166) | high | 41 | — | Stratified turbulence. |
| Ken Kamrin | Core | [A5023745556](https://openalex.org/A5023745556) | high | 224 | — | Granular mechanics (MIT -> UCB). |
| Homayoon Kazerooni | Core | [A5077696000](https://openalex.org/A5077696000) | high | 187 | — | Exoskeletons. |
| Kyriakos Komvopoulos | Core | [A5085102760](https://openalex.org/A5085102760) | high | 374 | — | Tribology, surface mechanics; 346 UCB works. |
| Liwei Lin | Core | [A5100383258](https://openalex.org/A5100383258) | medium | 822 | affiliation | Common name; OpenAlex profile (955 works) shows Sichuan/Changzhou affiliations => merged with namesakes. Papers kept only where Lin's authorship is UCB/LBL/Michigan/NTU or has no affiliation data. |
| Fai Ma | Core | [A5067606323](https://openalex.org/A5067606323) | high | 125 | — | Vibration/dynamics; last-known UCB. |
| Simo Mäkiharju | Core | [A5067189493](https://openalex.org/A5067189493) | high | 87 | — | Experimental fluids. |
| Sara McMains | Core | [A5028643684](https://openalex.org/A5028643684) | high | 92 | — | Geometry/graphics for manufacturing. |
| Negar Mehr | Core | [A5062267932](https://openalex.org/A5062267932), [A5098821351](https://openalex.org/A5098821351) | high | 74 | — | Main + small UCB split profile. |
| Emily Miller | Core | [A5087459214](https://openalex.org/A5087459214) | high | 22 | — | Emily Y. Miller (CU Boulder/Utah): osteoarthritis, MRI, knee injury - matches profile (computational biomechanics, ACL, cartilage MRI). 22 works. Starts Jan 2027. |
| Mohammad R. K. Mofrad | Core | [A5062246663](https://openalex.org/A5062246663) | high | 429 | — | Cell mechanics. |
| Mark W. Mueller | Core | [A5009591368](https://openalex.org/A5009591368) | high | 93 | — | Aerial robotics (ETH -> UCB). |
| Grace D. O’Connell | Core | [A5079024178](https://openalex.org/A5079024178) | high | 109 | — | Spine/disc biomechanics. |
| Oliver M. O’Reilly | Core | [A5069461742](https://openalex.org/A5069461742) | high | 229 | — | Dynamics; UCB 1993-. |
| Panayiotis Papadopoulos | Core | [A5102898265](https://openalex.org/A5102898265) | high | 118 | — | Computational mechanics; UCB 1990-. |
| Kameshwar Poolla | Core | [A5023927229](https://openalex.org/A5023927229) | high | 288 | — | Control/identification/smart grid. Bala Kameshwar Poolla (NREL) is a different person. |
| Lisa Pruitt | Core | [A5014712152](https://openalex.org/A5014712152) | high | 174 | — | Orthopaedic polymers/fatigue. |
| Michael D. Sangid | Core | [A5082636926](https://openalex.org/A5082636926) | high | 191 | — | Fatigue/microstructure (Purdue -> UCB 2026). |
| Thomas Schutzius | Core | [A5002685951](https://openalex.org/A5002685951) | high | 83 | — | Surfaces/icing (ETH -> UCB 2023). |
| Shawn Shadden | Core | [A5045646606](https://openalex.org/A5045646606) | high | 183 | — | Cardiovascular flows. |
| Lydia Sohn | Core | [A5063994602](https://openalex.org/A5063994602) | high | 142 | — | Microfluidic biosensing. |
| Koushil Sreenath | Core | [A5054075105](https://openalex.org/A5054075105), [A5124375628](https://openalex.org/A5124375628) | high | 211 | — | Main + 2025-26 UCB split profile (RL/locomotion). |
| David Steigmann | Core | [A5040589049](https://openalex.org/A5040589049) | high | 256 | — | Elasticity/shells. |
| Hannah Stuart | Core | [A5021360260](https://openalex.org/A5021360260) | high | 69 | — | Embodied dexterity / robotics. |
| Hayden Taylor | Core | [A5060055066](https://openalex.org/A5060055066) | medium | 108 | affiliation | Profile lists German Cancer Research Center / Essen (2019) => likely merged with a medical Hayden Taylor; affiliation filter applied. |
| Masayoshi Tomizuka | Core | [A5064077634](https://openalex.org/A5064077634), [A5098246986](https://openalex.org/A5098246986), [A5125041902](https://openalex.org/A5125041902) | high | 1044 | — | Main (1033 works) + two UCB split profiles (2025-26 robotics papers). |
| Lining Yao | Core | [A5052051114](https://openalex.org/A5052051114) | high | 171 | — | Morphing matter (CMU -> UCB 2024). |
| Tarek I. Zohdi | Core | [A5079030702](https://openalex.org/A5079030702), [A5108801978](https://openalex.org/A5108801978) | high | 375 | — | Main + small UCB split. |
| Murat Arcak | Joint | [A5025743742](https://openalex.org/A5025743742) | high | 389 | — | Control theory (EECS/ME). |
| Peter Hosemann | Joint | [A5090203585](https://openalex.org/A5090203585) | high | 386 | — | Nuclear materials. |
| Dorian Liepmann | Joint | [A5090887945](https://openalex.org/A5090887945) | high | 175 | — | Microfluidics / BioMEMS. |
| Robert O. Ritchie | Joint | [A5034751387](https://openalex.org/A5034751387) | high | 1028 | — | Fracture/fatigue; 1224 works, h=152. |
| S. Shankar Sastry | Joint | [A5062722286](https://openalex.org/A5062722286), [A5103101043](https://openalex.org/A5103101043) | high | 989 | — | CORRECTED: old graph used stub A5103101043 (5 works). Real profile A5062722286 (1271 works, h=120) + stub merged. |
| Somayeh Sojoudi | Joint | [A5072786751](https://openalex.org/A5072786751) | high | 184 | — | Optimization/control. |
| Alice M. Agogino | Professors of the Graduate School | [A5108365897](https://openalex.org/A5108365897) | high | 338 | — | Design, engineering education. |
| David B. Bogy | Professors of the Graduate School | [A5084588603](https://openalex.org/A5084588603) | high | 571 | — | Tribology / head-disk interface. |
| Carlos Fernandez-Pello | Professors of the Graduate School | [A5032164158](https://openalex.org/A5032164158), [A5077493033](https://openalex.org/A5077493033) | high | 345 | — | Two OpenAlex profiles (232 + 156 works, both UCB fire/combustion) merged. Spanish art-theory namesake excluded. |
| Boris Rubinsky | Professors of the Graduate School | [A5080256488](https://openalex.org/A5080256488) | high | 504 | — | Bioheat transfer / electroporation. |
| David M. Auslander | Emeritus | [A5072410143](https://openalex.org/A5072410143) | high | 220 | — | Mechatronics / building control. |
| James Casey | Emeritus | [A5080775953](https://openalex.org/A5080775953) | medium | 82 | affiliation, topic, field | OpenAlex profile merged with a historian (Univ. of East Anglia, medieval Spain). Affiliation + topic filter applied. |
| Jyh-Yuan Chen | Emeritus | [A5041673125](https://openalex.org/A5041673125), [A5025513890](https://openalex.org/A5025513890) | medium | 228 | affiliation, topic, field | Profile 'Jy Chen' (307 works) includes medical-education topics => merged with namesakes. Affiliation + topic filter. Small UCB stub merged. |
| Robert Dibble | Emeritus | [A5030860062](https://openalex.org/A5030860062) | high | 398 | — | Combustion engines. |
| Michael Frenklach | Emeritus | [A5078826017](https://openalex.org/A5078826017) | high | 295 | — | Combustion chemistry / soot. |
| Ralph Greif | Emeritus | [A5072930401](https://openalex.org/A5072930401) | high | 274 | — | Heat transfer. |
| George Johnson | Emeritus | [A5104032064](https://openalex.org/A5104032064) | high | 95 | — | George C. Johnson: elasticity, ultrasonics, MEMS; UCB 1981-2012. |
| Tony M. Keaveny | Emeritus | [A5060491136](https://openalex.org/A5060491136) | high | 273 | — | Bone biomechanics. |
| Dennis K. Lieu | Emeritus | [A5109856231](https://openalex.org/A5109856231) | high | 71 | — | Electric motors / magnetics. |
| Philip S. Marcus | Emeritus | [A5067592185](https://openalex.org/A5067592185) | high | 224 | — | Geophysical/astrophysical fluid dynamics. |
| Ömer Savaş | Emeritus | [A5101920368](https://openalex.org/A5101920368) | high | 110 | — | Experimental fluid mechanics; UCB 1992-2024. Turkish namesakes (welding, medicine) excluded. |
| Benson H. Tongue | Emeritus | [A5109858875](https://openalex.org/A5109858875) | high | 86 | — | Vibrations / vehicle dynamics. |
| Paul K. Wright | Emeritus | [A5102817905](https://openalex.org/A5102817905) | medium | 366 | affiliation, topic, field | Profile shows NIH / Northwell / Alberta Health affiliations => merged with a medical Paul Wright. Affiliation + topic filter applied. |
| Kazuo Yamazaki | Emeritus | [A5102847358](https://openalex.org/A5102847358) | high | 202 | — | Machining/CAD-CAM (UC Davis / UCB). |
| Ronald W. Yeung | Emeritus | [A5037167646](https://openalex.org/A5037167646) | high | 155 | — | Ship hydrodynamics; UCB 1972-. |
| Xiang Zhang | Emeritus | [A5100368854](https://openalex.org/A5100368854) | medium | 757 | affiliation | Very common name; profile (776 works, plasmonics/metamaterials) looks correct but affiliation filter applied as a guard. |
| George Anwar | Lecturers | [A5059299504](https://openalex.org/A5059299504) | high | 15 | — | Lecturer; control systems; UCB 1986-2021. |
| Gabriel Gomes | Lecturers | [A5102923214](https://openalex.org/A5102923214) | high | 59 | — | Lecturer; traffic control (PATH). |
| Ala Moradian | Lecturers | [A5114033252](https://openalex.org/A5114033252), [A5114408654](https://openalex.org/A5114408654) | medium | 9 | — | Lecturer. Toronto-era fluid/heat-transfer papers (8) + Applied Materials digital-twin chapter (1). Industrial career mostly patents (not indexed). |
| K. Youssefi | Lecturers | — | low | 0 | — | Lecturer; no OpenAlex author record found for 'Kamran Youssefi' / 'K. Youssefi'. Excluded from embedding. |
| David Horsley | Adjunct | [A5050152050](https://openalex.org/A5050152050) | high | 239 | — | MEMS ultrasound (UC Davis adjunct); id validated in previous iteration. |
| Samuel Mao | Adjunct | [A5089506493](https://openalex.org/A5089506493) | high | 247 | — | Laser materials / photocatalysis; appeared as UCB-affiliated candidate (167 UCB works). |
| Vassilia Zorba | Adjunct | [A5037594089](https://openalex.org/A5037594089) | high | 162 | — | Laser spectroscopy (LBL); id validated in previous iteration. |

## Attribution audit — removed assignments

Rule: (year < career start − 8) OR (primary OpenAlex field outside engineering/physical sciences AND no Berkeley/LBL/LLNL/Sandia affiliation on that paper AND leave-one-out similarity to the person's own papers in the bottom 5 %).

**Van P. Carey** (1):
- 2009 · Arts and Humanities · Professor Yogesh Jaluria on his 60th birthday (`W1973463269`)

**Chris Dames** (1):
- 2018 · Arts and Humanities · My Collaboration with Millie (`W2888493748`)

**Costas Grigoropoulos** (2):
- 2023 · Arts and Humanities · In Memoriam: Richard J. Goldstein (`W4366764800`)
- 2023 · Arts and Humanities · In Memoriam: Richard J. Goldstein (`W4367046933`)

**Roberto Horowitz** (3):
- 2012 · Psychology · An exploratory study of the impact of college student leadership programs upon the construct of mindfulness (`W2275216808`)
- 2024 · Psychology · Are We Missing Opportunities to Avoid Guardianship Proceedings in Unrepresented Hospitalized Patients? (`W4396530499`)
- 2009 · Medicine · Autopsies: an exercise in futility? (`W4406153508`)

**Ken Kamrin** (1):
- 2023 · Neuroscience · Bioinspired, ingestible electroceutical capsules for hunger-regulating hormone modulation (`W4367042145`)

**Liwei Lin** (1):
- 2004 · Health Professions · Evaluation in Design of Taipei City Emergency Operations Center (`W2189564944`)

**Mohammad R. K. Mofrad** (1):
- 2012 · Neuroscience · Brain Implants (`W4233868894`)

**Kameshwar Poolla** (1):
- 2021 · Arts and Humanities · Andrew K. Packard (July 7, 1960 - September 30, 2019) [Obituary] (`W3165573188`)

**Michael D. Sangid** (1):
- 2021 · Biochemistry, Genetics and Molecular Biology · 3D Fiber Segmentation with Deep Center Regression and Geometric Clustering (`W3184506919`)

**Thomas Schutzius** (1):
- 2022 · Biochemistry, Genetics and Molecular Biology · Bistability of Dielectrically Anisotropic Nematic Crystals and the Adaptation of Endothelial Collectives to St (`W4221024887`)

**Lydia Sohn** (1):
- 2005 · Social Sciences · Reflections on Conversation Two (`W2495530358`)

**David Steigmann** (1):
- 2002 · Arts and Humanities · Eugen Soóos (`W2464182799`)

**Masayoshi Tomizuka** (3):
- 1997 · Arts and Humanities · Yasundo Takahashi (1912-1996) (`W2029302868`)
- 1990 · Arts and Humanities · The Second Ten Years of the JDSM&C (`W2079663329`)
- 2009 · Arts and Humanities · Succeeding a Dream of My Father (`W2313866777`)

**Peter Hosemann** (5):
- 1967 · Earth and Planetary Sciences · Authigenic High Sanidine from Western Australia (`W1992834835`)
- 1970 · Earth and Planetary Sciences · Optical data on some authigenic feldspars from Western Australia (`W2018172065`)
- 1971 · Earth and Planetary Sciences · THE STRATIGRAPHY OF THE BASAL TRIASSIC SANDSTONE, NORTH PERTH BASIN, WESTERN AUSTRALIA (`W2747127102`)
- 1978 · Engineering · The role of hydrogen development in hypothetical core meltdown (`W3183652117`)
- 1995 · Social Sciences · International cooperation in safety research. The CORVIS-project of the Paul Scherrer Institute (`W3183977062`)

**Somayeh Sojoudi** (2):
- 2014 · Medicine · Robust efficiency and actuator saturation explain healthy heart rate control and variability (`W2041461641`)
- 2015 · Neuroscience · Corpus Callosum Area and Brain Volume in Autism Spectrum Disorder: Quantitative Analysis of Structural MRI fro (`W603975957`)

**James Casey** (6):
- 1952 · Engineering · REPORT ON DISTRIBUTION STUDIES BETWEEN MELTS AND SOLID PHASES USING RADIOACTIVE TRACERS (`W103257949`)
- 1961 · Physics and Astronomy · Capillary Alloying: An Improved Alloying Method (`W1988121721`)
- 1966 · Physics and Astronomy · FEASIBILITY STUDY OF METAL BASE TRANSISTORS. (`W2010439229`)
- 1964 · Physics and Astronomy · Evaluation of Concentration Distributions by Test Diffusion and Junction Delineation (`W2093221511`)
- 1955 · Chemistry · Formation of Ce2O3·2ZrO2 in the System BaCl2-CeCl3-BaZrO31 (`W2280850591`)
- 1925 · Environmental Science · CAMBRIDGE SYSTEM OF REAL ESTATE VALUATIONS (`W3136558558`)

**Robert Dibble** (1):
- 1958 · Engineering · Aircraft Nuclear Propulsion Department. Administrative Report (`W3132743334`)

**Michael Frenklach** (1):
- 2003 · Arts and Humanities · An Optimization/IT Theory Approach to the HOx Dilemma, Data, and Modeling (`W3081880661`)

**George Johnson** (1):
- 1961 · Chemical Engineering · Flow Characteristics of Linear, End-Blocked Dimethylpolysiloxane Fluids. (`W2000530634`)

**Dennis K. Lieu** (1):
- 2006 · Biochemistry, Genetics and Molecular Biology · HCN-Encoded Pacemaker Channels: From Physiology and Biophysics to Bioengineering (`W1983563548`)

**Paul K. Wright** (13):
- 2012 · Neuroscience · Differentiating Hemispheric Contributions to Syntax and Semantics in Patients with Left-Hemisphere Lesions (`W1975651116`)
- 2013 · Neuroscience · Objects and Categories: Feature Statistics and Object Processing in the Ventral Stream (`W1997045645`)
- 2015 · Neuroscience · The perirhinal cortex and conceptual processing: Effects of feature-based statistics following damage to the a (`W2013126441`)
- 2012 · Neuroscience · Age-related Neural Reorganization during Spoken Word Recognition: The Interaction of Form and Meaning (`W2033977972`)
- 2014 · Neuroscience · Age-related sensitivity to task-related modulation of language-processing networks (`W2039126991`)
- 2010 · Neuroscience · Dissociating Linguistic and Task-related Activity in the Left Inferior Frontal Gyrus (`W2041872868`)
- 2011 · Neuroscience · Left inferior frontal cortex and syntax: function, structure and behaviour in patients with left hemisphere da (`W2119150045`)
- 2010 · Neuroscience · Reorganization of syntactic processing following left-hemisphere brain damage: does right-hemisphere activity  (`W2135303411`)
- 2015 · Neuroscience · Idiosyncratic responding during movie-watching predicted by age differences in attentional control (`W2165123258`)
- 2009 · Neuroscience · Preserving Syntactic Processing across the Adult Life Span: The Modulation of the Frontotemporal Language Syst (`W2172014431`)
- 2010 · Social Sciences · China: behind the bamboo curtain (`W2545313198`)
- 2007 · Social Sciences · Betulia Liberata in Perth (`W2725314448`)
- 2008 · Social Sciences · Prisoners’ Guerrilla Handbook to Correspondence Programs in the United States and Canada (third edition) by Jo (`W3159368788`)

**Kazuo Yamazaki** (2):
- 1997 · Business, Management and Accounting · A study on shifting towards multiculture-based manufacturing to promote society — Observations and strategies  (`W2049666669`)
- 1974 · Engineering · Study on Adaptive Control in an NC Milling Machine (`W2315776078`)

**Xiang Zhang** (1):
- 2016 · Biochemistry, Genetics and Molecular Biology · Application of Wavelet Transform Algorithm and Rolling Ball Algorithm in Single Molecule Fluorescence Resonanc (`W2579551908`)

**David Horsley** (5):
- 2014 · Biochemistry, Genetics and Molecular Biology · Faster-than-anticipated Na+/Cl− diffusion across lipid bilayers in vesicles (`W1974859001`)
- 1991 · Biochemistry, Genetics and Molecular Biology · Fluorescence quenching of adsorbed hen and human lysozymes (`W2010842482`)
- 2006 · Biochemistry, Genetics and Molecular Biology · Mapping protein collapse with single-molecule fluorescence and kinetic synchrotron radiation circular dichrois (`W2050463871`)
- 2015 · Medicine · 11.8 Integrated ultrasonic system for measuring body-fat composition (`W2055570207`)
- 2010 · Biochemistry, Genetics and Molecular Biology · Magnetic scanometric DNA microarray detection of methyl tertiary butyl ether degrading bacteria for environmen (`W2113692970`)

**Vassilia Zorba** (2):
- 2020 · Medicine · Additional file 2 of A comprehensive analysis of sialolith proteins and the clinical implications (`W4394077086`)
- 2020 · Medicine · Additional file 5 of A comprehensive analysis of sialolith proteins and the clinical implications (`W4394126181`)

## Signals per faculty (informational)

`early` = papers more than 5 years before the first 3-papers-in-3-years window; `field_mismatch` = dropped by the field rule; `cluster_flag` = a 2-means split of the person's papers yields a distant minority cluster with no plausible affiliation (worth a manual look).

| Faculty | papers | career start | early | field mismatch | cluster flag | minority cluster topics |
|---|---:|---:|---:|---:|---|---|
| Behçet Açıkmeşe | 261 | 2005 | 0 | 0 | no | Spacecraft Dynamics and Control, Robotic Path Planning Algorithms |
| M. Reza Alam | 136 | 2005 | 0 | 0 | no | Micro and Nano Robotics, Fluid dynamics and aerodynamics studies |
| Francesco Borrelli | 357 | 2000 | 0 | 0 | no | Vehicle Dynamics and Control Systems, Traffic control and management |
| Van P. Carey | 295 | 1977 | 0 | 1 | no | Heat Transfer and Optimization, Phase Change Materials Research |
| Chris Dames | 166 | 1994 | 0 | 1 | no | Ferroelectric and Piezoelectric Materials, Thermal properties of materials |
| Michael Gollner | 160 | 2010 | 0 | 0 | no | Fire dynamics and safety research, Combustion and flame dynamics |
| Salvador Rey Gomez | 8 | 2023 | 0 | 0 | no |  |
| Kosa Goucher-Lambert | 101 | 2014 | 0 | 0 | no | Design Education and Practice, Human-Automation Interaction and Safety |
| Costas Grigoropoulos | 602 | 1986 | 0 | 2 | no | 2D Materials and Applications, Nanomaterials and Printing Technologies |
| Grace X. Gu | 146 | 2014 | 0 | 0 | no | Machine Learning in Materials Science, Additive Manufacturing and 3D Printing Technologies |
| Claudio Hail | 36 | 2015 | 0 | 0 | **yes** | Tribology and Lubrication Engineering, Advanced Thermodynamic Systems and Engines |
| Roberto Horowitz | 466 | 1983 | 0 | 3 | no | Traffic control and management, Vehicle Dynamics and Control Systems |
| Alexis Kaminski | 41 | 2012 | 0 | 0 | no | Oceanographic and Atmospheric Processes, Fluid Dynamics and Turbulent Flows |
| Ken Kamrin | 225 | 2005 | 0 | 1 | no | Elasticity and Wave Propagation, Advanced Numerical Methods in Computational Mathematics |
| Homayoon Kazerooni | 187 | 1984 | 0 | 0 | no | Prosthetics and Rehabilitation Robotics, Ergonomics and Musculoskeletal Disorders |
| Kyriakos Komvopoulos | 374 | 1985 | 0 | 0 | no | Metal and Thin Film Mechanics, Diamond and Carbon-based Materials Research |
| Liwei Lin | 823 | 1992 | 1 | 1 | no | Advanced Sensor and Energy Harvesting Materials, Supercapacitor Materials and Fabrication |
| Fai Ma | 125 | 1981 | 0 | 0 | no | Vibration and Dynamic Analysis, Matrix Theory and Algorithms |
| Simo Mäkiharju | 87 | 2007 | 0 | 0 | no | Fluid Dynamics and Turbulent Flows, Advanced X-ray Imaging Techniques |
| Sara McMains | 92 | 1998 | 0 | 0 | no | Computer Graphics and Visualization Techniques, Advanced Numerical Analysis Techniques |
| Negar Mehr | 74 | 2016 | 0 | 0 | no | Traffic control and management, Vehicle Routing Optimization Methods |
| Emily Miller | 22 | 2020 | 0 | 0 | no | Muscle Physiology and Disorders, Cellular Mechanics and Interactions |
| Mohammad R. K. Mofrad | 430 | 1999 | 0 | 1 | no | Nuclear Structure and Function, Machine Learning in Bioinformatics |
| Mark W. Mueller | 93 | 2012 | 0 | 0 | no | Robotics and Sensor-Based Localization, Robotic Path Planning Algorithms |
| Grace D. O’Connell | 109 | 2006 | 0 | 0 | no | Osteoarthritis Treatment and Mechanisms, Effects of Radiation Exposure |
| Oliver M. O’Reilly | 229 | 1990 | 0 | 0 | no | Dynamics and Control of Mechanical Systems, Experimental and Theoretical Physics Studies |
| Panayiotis Papadopoulos | 118 | 1990 | 0 | 0 | no | Elasticity and Wave Propagation, Dynamics and Control of Mechanical Systems |
| Kameshwar Poolla | 289 | 1983 | 0 | 1 | no | Electric Power System Optimization, Smart Grid Energy Management |
| Lisa Pruitt | 174 | 1986 | 0 | 0 | no | Orthopaedic implants and arthroplasty, Fatigue and fracture mechanics |
| Michael D. Sangid | 192 | 2010 | 0 | 1 | no | Mechanical Behavior of Composites, Injection Molding Process and Properties |
| Thomas Schutzius | 84 | 2009 | 0 | 1 | no | Surface Modification and Superhydrophobicity, Electrowetting and Microfluidic Technologies |
| Shawn Shadden | 183 | 2004 | 0 | 0 | no | Fluid Dynamics and Turbulent Flows, Quantum chaos and dynamical systems |
| Lydia Sohn | 143 | 1991 | 0 | 1 | no | Nanopore and Nanochannel Transport Studies, Physics of Superconductivity and Magnetism |
| Koushil Sreenath | 211 | 2005 | 0 | 0 | no | Robotic Path Planning Algorithms, Formal Methods in Verification |
| David Steigmann | 257 | 1986 | 0 | 1 | no | Lipid Membrane Structure and Behavior, Elasticity and Material Modeling |
| Hannah Stuart | 69 | 2012 | 0 | 0 | no | Prosthetics and Rehabilitation Robotics, Tactile and Sensory Interactions |
| Hayden Taylor | 108 | 2004 | 0 | 0 | no | Nanofabrication and Lithography Techniques, Surface Modification and Superhydrophobicity |
| Masayoshi Tomizuka | 1047 | 1973 | 0 | 3 | no | Autonomous Vehicle Technology and Safety, Robot Manipulation and Learning |
| Lining Yao | 171 | 2009 | 0 | 0 | no | Interactive and Immersive Displays, Innovative Human-Technology Interaction |
| Tarek I. Zohdi | 375 | 1996 | 0 | 0 | no | Advanced Numerical Methods in Computational Mathematics, Mathematical and Theoretical Epidemiology and Ecology Models |
| Murat Arcak | 389 | 1998 | 0 | 0 | no | Nonlinear Dynamics and Pattern Formation, Control and Stability of Dynamical Systems |
| Peter Hosemann | 391 | 2005 | 5 | 1 | no | Fusion materials and technologies, Nuclear Materials and Properties |
| Dorian Liepmann | 175 | 1988 | 0 | 0 | no | Microfluidic and Capillary Electrophoresis Applications, Fluid Dynamics and Turbulent Flows |
| Robert O. Ritchie | 1028 | 1971 | 0 | 0 | no | Bone health and osteoporosis research, Calcium Carbonate Crystallization and Inhibition |
| S. Shankar Sastry | 989 | 1980 | 0 | 0 | no | Advanced Vision and Imaging, Control and Dynamics of Mobile Robots |
| Somayeh Sojoudi | 186 | 2007 | 0 | 2 | no | Adversarial Robustness in Machine Learning, Advanced Graph Neural Networks |
| Alice M. Agogino | 338 | 1985 | 1 | 0 | no | Advanced MEMS and NEMS Technologies, Soft Robotics and Applications |
| David B. Bogy | 571 | 1962 | 0 | 0 | no | Elasticity and Wave Propagation, Electromagnetic Scattering and Analysis |
| Carlos Fernandez-Pello | 345 | 1975 | 0 | 0 | no | Fire dynamics and safety research, Advanced Combustion Engine Technologies |
| Boris Rubinsky | 504 | 1977 | 0 | 0 | no | Microbial Inactivation Methods, Electrical and Bioimpedance Tomography |
| David M. Auslander | 220 | 1968 | 0 | 0 | no | Smart Grid Energy Management, Building Energy and Comfort Optimization |
| James Casey | 88 | 1978 | 6 | 0 | no | Advanced Differential Geometry Research, Mathematics and Applications |
| Jyh-Yuan Chen | 228 | 1987 | 0 | 0 | no | Combustion and flame dynamics, Advanced Combustion Engine Technologies |
| Robert Dibble | 399 | 1978 | 1 | 0 | no | Combustion and flame dynamics, Advanced Combustion Engine Technologies |
| Michael Frenklach | 296 | 1975 | 0 | 1 | no | Advanced Combustion Engine Technologies, Diamond and Carbon-based Materials Research |
| Ralph Greif | 274 | 1958 | 0 | 0 | no | Laser Material Processing Techniques, Laser-induced spectroscopy and plasma |
| George Johnson | 96 | 1979 | 1 | 0 | no | Advanced MEMS and NEMS Technologies, Ultrasonics and Acoustic Wave Propagation |
| Tony M. Keaveny | 273 | 1993 | 0 | 0 | no | Bone health and osteoporosis research, Hormonal and reproductive studies |
| Dennis K. Lieu | 72 | 1983 | 0 | 1 | no | Soil Mechanics and Vehicle Dynamics, Engineering Education and Pedagogy |
| Philip S. Marcus | 224 | 1977 | 0 | 0 | no | Astro and Planetary Science, Astrophysics and Star Formation Studies |
| Ömer Savaş | 110 | 1983 | 0 | 0 | no | Cerebrovascular and Carotid Artery Diseases, Intracranial Aneurysms: Treatment and Complications |
| Benson H. Tongue | 86 | 1983 | 0 | 0 | no | Mathematical Dynamics and Fractals, Control Systems and Identification |
| Paul K. Wright | 379 | 1974 | 0 | 13 | no | Innovative Energy Harvesting Technologies, Advanced Thermoelectric Materials and Devices |
| Kazuo Yamazaki | 204 | 1983 | 2 | 1 | no | Advanced Machining and Optimization Techniques, Additive Manufacturing Materials and Processes |
| Ronald W. Yeung | 155 | 1973 | 0 | 0 | no | Wave and Wind Energy Systems, Wind Energy Research and Development |
| Xiang Zhang | 758 | 1994 | 0 | 1 | no | 2D Materials and Applications, Metamaterials and Metasurfaces Applications |
| George Anwar | 15 | 1986 | 0 | 0 | no |  |
| Gabriel Gomes | 59 | 1999 | 0 | 0 | no | Traffic control and management, Transport Systems and Technology |
| Ala Moradian | 9 | 2005 | 0 | 0 | no |  |
| David Horsley | 244 | 1987 | 0 | 5 | no | Ultrasonics and Acoustic Wave Propagation, Acoustic Wave Resonator Technologies |
| Samuel Mao | 247 | 1994 | 0 | 0 | no | Laser Material Processing Techniques, Laser-induced spectroscopy and plasma |
| Vassilia Zorba | 164 | 2002 | 0 | 2 | no | Orbital Angular Momentum in Optics, Optical Wireless Communication Technologies |

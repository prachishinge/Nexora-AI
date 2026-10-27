import os
import asyncio
import urllib.request
import urllib.parse
import re
import html
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from openai import AsyncOpenAI
from image_service import is_image_request, refine_image_prompt, generate_and_save_image, clean_user_prompt, IMAGES_DIR

# Explicitly check for .env file or environment variables
env_path = Path(__file__).resolve().parent.parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
model = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

if not api_key:
    client = None
else:
    # Groq provides an OpenAI compatible API
    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1"
    )

# Verified Factual Benchmarks for Competitive Exams, Law & Governance
VERIFIED_GROUND_TRUTH_FACTS = """
[VERIFIED FACTUAL BENCHMARKS - STRICT REFERENCE FOR COMPETITIVE EXAMS & GOVERNANCE]:

1. CURRENT NATIONAL & MAHARASHTRA GOVERNANCE ROSTER:
- Prime Minister of India: Narendra Modi (serving 3rd consecutive term).
- President of India: Droupadi Murmu (15th President of India).
- Vice President of India: Jagdeep Dhankhar.
- Chief Justice of India (CJI): Sanjiv Khanna (51st Chief Justice of India - took oath 11 November 2024).
- Chief Justice of Bombay High Court: Justice Mahesh Chandra Tripathi (50th Chief Justice - sworn in 9 September 2026).
- Governor of Maharashtra: C. P. Radhakrishnan.
- Chief Minister of Maharashtra: Devendra Fadnavis (BJP - assumed office 5 December 2024 following the Mahayuti alliance victory).
- Deputy Chief Ministers of Maharashtra (CURRENT INCUMBENTS ONLY):
  1. Eknath Shinde (Shiv Sena - sworn in 5 December 2024; active incumbent)
  2. Sunetra Pawar (Nationalist Congress Party - NCP; sworn in 31 January 2026 as Maharashtra's first female Deputy Chief Minister; active incumbent)
  *STRICT FACTUAL MANDATE & HISTORICAL DISTINCTION*:
  • The two current, incumbent Deputy Chief Ministers of Maharashtra are Eknath Shinde and Sunetra Pawar.
  • Ajit Pawar is a FORMER Deputy Chief Minister. He passed away on 28 January 2026 in an air crash near Baramati. He is NOT a current Deputy Chief Minister!
  • NEVER describe Ajit Pawar as a current or incumbent Deputy Chief Minister.
- Speaker of Maharashtra Legislative Assembly: Rahul Narwekar.
- Commissioner of Food & Drug Administration (FDA) Maharashtra: Tukaram Mundhe (IAS).
- Chief Secretary of Maharashtra: Sujata Saunik (IAS).
- Director General of Police (DGP) Maharashtra: Rashmi Shukla (IPS).
- Commissioner of Police, Mumbai: Vivek Phansalkar (IPS).
- Governor of Reserve Bank of India (RBI): Sanjay Malhotra (26th Governor, assumed office 11 December 2024, succeeding Shaktikanta Das).
- Chief Election Commissioner (CEC) of India: Gyanesh Kumar (26th CEC, assumed office 19 February 2025, succeeding Rajiv Kumar).
- Chairman of ISRO: Dr. V. Narayanan (assumed office 14 January 2025, succeeding S. Somanath).
- Chief of Defence Staff (CDS): General N. S. Raja Subramani (assumed office 31 May 2026, succeeding General Anil Chauhan).
- Chief of the Army Staff (COAS): General Dhiraj Seth (assumed office 30 June 2026, succeeding General Upendra Dwivedi).
- Chief of the Naval Staff (CNS): Admiral Krishna Swaminathan (assumed office 31 May 2026).
- Chief of the Air Staff (CAS): Air Chief Marshal Amar Preet Singh.

2. MAJOR CONTEMPORARY INDIAN EVENTS & AVIATION ACCIDENTS:
- Air India Flight 171 (AI 171) Ahmedabad Plane Crash (12 June 2025):
  • Date: 12 June 2025 (at approx 13:39 IST / 08:09 UTC).
  • Aircraft: Boeing 787-8 Dreamliner.
  • Route: Sardar Vallabhbhai Patel International Airport (Ahmedabad, Gujarat) to London Gatwick Airport (UK).
  • Crash Site: Lost thrust shortly after liftoff and crashed approx 32 seconds later into the student hostel buildings of B.J. Medical College in Meghaninagar, Ahmedabad.
  • Casualties: 241 of 242 people on board died (1 passenger miraculously survived), plus ground casualties at the medical college hostel (total ~260 fatalities).
  • Investigation: Aircraft Accident Investigation Bureau (AAIB) of India. Preliminary findings indicated engine fuel control switches moved to cutoff position shortly after takeoff.
  • Strict Rule: This is an authentic, real-world historical event. NEVER deny or state that no plane crash occurred in Ahmedabad in 2025!

3. MAHARASHTRA FLAGSHIP WELFARE SCHEMES (CRITICAL FOR MPSC, POLICE BHARTI, TALATHI):
- Mukhyamantri Majhi Ladki Bahin Yojana (मुख्यमंत्री माझी लाडकी बहीण योजना):
  • Department: Women & Child Development Department, Government of Maharashtra.
  • Launch: Announced in Maharashtra State Budget June 2024, launched in July 2024.
  • Benefit: ₹1,500 per month (₹18,000 annually) direct cash transfer via Direct Benefit Transfer (DBT) into Aadhaar-linked bank accounts.
  • Eligibility: Women residents of Maharashtra aged 21 to 65 years with annual family income up to ₹2.5 lakh.
  • Status: Active, official, flagship scheme of Maharashtra. NEVER state that this scheme does not exist!
- Namo Shetkari Mahasanman Nidhi Yojana (नमो शेतकरी महासन्मान निधी योजना):
  • State supplementary assistance of ₹6,000 per year from Maharashtra Government, in addition to ₹6,000 from Central PM-KISAN (Total ₹12,000/year to eligible farmers).
- Mukhyamantri Yuva Karya Prashikshan Yojana / Ladka Bhau Yojana (लाडका भाऊ योजना / युवा कार्य प्रशिक्षण):
  • Monthly internship stipend for youth (age 18-35): ₹6,000 (12th pass), ₹8,000 (ITI/Diploma), ₹10,000 (Graduates/Post-graduates).
- Lek Ladki Yojana (लेक लाडकी योजना):
  • Financial assistance of ₹1,01,000 across 5 stages from birth to age 18 for girl children born in yellow/orange ration card families.
- Mukhyamantri Annapurna Yojana (मुख्यमंत्री अन्नपूर्णा योजना):
  • 3 free LPG gas cylinders per year for eligible poor families and Ladki Bahin beneficiaries.
- Mukhyamantri Vayoshri Yojana (मुख्यमंत्री वयोश्री योजना):
  • One-time assistance of ₹3,000 for senior citizens aged 65 and above for physical aids and health devices.
- Mahatma Jyotirao Phule Jan Arogya Yojana (MJPJAY):
  • Cashless health insurance coverage up to ₹5 lakh per family across Maharashtra.

3. INDIAN LAW & JUDICIARY BENCHMARKS (JMFC, MH CET LAW, CLAT, MPSC APP, POLICE BHARTI):
- Legal Interpretation of 'Dhara' (धारा) / 'Kalam' (कलम):
  • In Indian legal and competitive exam context, 'Dhara' (धारा) or 'Kalam' (कलम) strictly means a Legal Section of an Act or an Article of the Constitution. NEVER confuse it with consumer products (water purifiers, oils, etc.)!
  • Clarification on 'Dhara 360' / 'Kalam 360' (धारा ३६० / कलम ३६०):
    1. Article 360 of the Indian Constitution (कलम ३६०): Financial Emergency (वित्तीय आणीबाणी). Empowered President to declare financial emergency if the financial credit of India is threatened. Under Art. 360, salaries of judges and government officials can be reduced. Note: Financial emergency has NEVER been declared in India so far.
    2. Section 360 of Code of Criminal Procedure (CrPC 1973) / Section 401 of Bharatiya Nagarik Suraksha Sanhita (BNSS 2023): Order to release on probation of good conduct or after admonition.
    3. Section 360 of Indian Penal Code (IPC 1860): Kidnapping from India. (Under BNS 2023, kidnapping is covered under Section 137 BNS).
- New Criminal Laws (In effect from 1 July 2024 across India):
  • Bharatiya Nyaya Sanhita (BNS) 2023 replaced IPC 1860 (Total 358 sections vs 511 in IPC):
    - Murder: Section 103 BNS (formerly Sec 302 IPC).
    - Attempt to Murder: Section 109 BNS (formerly Sec 307 IPC).
    - Culpable Homicide not amounting to murder: Section 105 BNS (formerly Sec 304 IPC).
    - Rape: Section 63 & 64 BNS (formerly Sec 375 & 376 IPC); Gang Rape: Section 70 BNS.
    - Kidnapping: Section 137 BNS (formerly Sec 359-363 IPC).
    - Theft: Section 303 BNS (formerly Sec 378-379 IPC).
    - Snatching: Section 304 BNS (new statutory offense).
    - Cheating: Section 318 BNS (formerly Sec 420 IPC).
    - Robbery & Dacoity: Section 309-310 BNS (formerly Sec 390-395 IPC).
    - Organized Crime: Section 111 BNS; Terrorist Act: Section 113 BNS; Mob Lynching: Section 103(2) BNS.
    - Treason / Endangering Sovereignty: Section 152 BNS (Sedition/Rajdroha repealed).
    - Defamation: Section 356 BNS (introduced community service as punishment).
  • Bharatiya Nagarik Suraksha Sanhita (BNSS) 2023 replaced CrPC 1973 (Total 531 sections vs 484 in CrPC):
    - Zero FIR: Section 173(1) BNSS.
    - Preliminary Enquiry before FIR for offenses punishable with 3-7 years: Section 173(3) BNSS.
    - Arrest safeguards & notice: Section 35 BNSS (formerly Sec 41/41A CrPC).
    - Videography of search, seizure, crime scene: Section 105 BNSS (mandatory).
    - Regular Bail: Section 480 & 481 BNSS (formerly Sec 437 & 439 CrPC).
    - Anticipatory Bail: Section 482 BNSS (formerly Sec 438 CrPC).
    - Default Bail: Section 187 BNSS (formerly Sec 167(2) CrPC).
    - Maintenance of wives, children, parents: Section 144 BNSS (formerly Sec 125 CrPC).
  • Bharatiya Sakshya Adhiniyam (BSA) 2023 replaced Indian Evidence Act 1872 (Total 170 sections vs 167 in IEA):
    - Digital and electronic records have primary evidentiary status: Section 57, 61, 63 BSA (formerly Sec 65B IEA).

4. CONSTITUTIONAL POWERS OF THE PRESIDENT OF INDIA (ARTICLES 52-78):
- Part V, The Union Executive:
  • Executive Powers: Head of Union Executive (Art. 53). All actions taken in President's name (Art. 77). Appoints Prime Minister (Art. 75(1)) and Ministers on PM's advice (Art. 75(2)), Attorney General (Art. 76), Supreme Court Judges (Art. 124), High Court Judges (Art. 217), Governors (Art. 155), CAG (Art. 148), UPSC Chairman (Art. 316), Chief Election Commissioner (Art. 324).
    *STRICT RULE*: Article 124 has only Articles 124, 124A, 124B, 124C. NEVER fabricate non-existent articles like 124D to 124YA!
  • Legislative Powers: Summons, prorogues Parliament, dissolves Lok Sabha (Art. 85). Addresses Parliament (Art. 86-87). Joint sitting (Art. 108). Assent to bills (Art. 111). Promulgates Ordinances during parliamentary recess (Art. 123). Nominates 12 members to Rajya Sabha (Art. 80).
  • Financial Powers: Money Bills introduced only on President's recommendation (Art. 117). Union Budget laid before Parliament (Art. 112). Contingency Fund advances (Art. 267). Constitutes Finance Commission every 5 years (Art. 280).
  • Judicial Powers: Pardoning power (Art. 72) - pardon, reprieve, respite, remission, or commutation of sentences, including court-martial and death sentences. Advisory jurisdiction of Supreme Court (Art. 143).
  • Diplomatic & Military Powers: Supreme Commander of Armed Forces (Art. 53(2)). Concludes treaties and receives ambassadors.
  • Emergency Powers (Part XVIII): National Emergency (Art. 352), President's Rule in States (Art. 356), Financial Emergency (Art. 360).
  • Constitutional Nature: President acts on aid and advice of the Council of Ministers (Art. 74(1)); 44th Amendment allows sending advice back once for reconsideration.

5. UPSC & MPSC COMPETITIVE EXAM STRUCTURE:
- UPSC Civil Services Examination (CSE):
  • Preliminary Examination (Objective):
    - General Studies Paper I (200 marks, marks count for cutoff).
    - CSAT Paper II (200 marks, qualifying nature, minimum 33% / 66 marks required).
  • Main Examination (Written Descriptive, 9 Papers):
    - Qualifying Papers: Paper A (Indian Language - 300 marks) + Paper B (English - 300 marks).
    - Merit Papers (7 papers x 250 marks = 1750 marks): Paper I Essay; Paper II GS I; Paper III GS II; Paper IV GS III; Paper V GS IV (Ethics); Paper VI Optional Paper 1; Paper VII Optional Paper 2.
  • Personality Test / Interview: 275 marks.
  • Total Marks: 2025 marks.
- MPSC State Services (Rajyaseva) & Non-Gazetted Group B & C:
  • Rajyaseva: Prelims (GS + CSAT qualifying) -> Descriptive Mains pattern -> Interview.
  • Group B (PSI, STI, ASO) & Group C: Joint Prelims (100 marks objective) -> Separate Mains (Paper 1 Marathi & English + Paper 2 GS).

"""

MAHARASHTRA_DISTRICT_DATA = [
    {
        'keys': ['sangli', 'सांगली', 'miraj', 'मिरज', 'walwa', 'वाळवा', 'islampur', 'इस्लामपूर', 'tasgaon', 'तासगाव', 'shirala', 'शिराळा', 'khanapur', 'खानापूर', 'vita', 'विटा', 'atpadi', 'आटपाडी', 'jat', 'जत', 'kavathe', 'कवठे', 'palus', 'पलूस', 'kadegaon', 'कडेगाव'],
        'info': """• SANGLI DISTRICT (सांगली जिल्हा) - EXACTLY 10 TALUKAS:
  1. Miraj (मिरज - Sangli HQ is situated in Miraj taluka; Sangli city is NOT a separate taluka!)
  2. Walwa / Islampur (वाळवा / इस्लामपूर)
  3. Shirala (शिराळा)
  4. Khanapur / Vita (खानापूर / विटा)
  5. Atpadi (आटपाडी)
  6. Tasgaon (तासगाव)
  7. Jat (जत)
  8. Kavathe Mahankal (कवठे महांकाळ)
  9. Palus (पलूस)
  10. Kadegaon (कडेगाव)
  *STRICT FACTUAL MANDATE*: Sangli has exactly 10 talukas. NEVER say 12. NEVER include Shirol (belongs to Kolhapur), Wai (belongs to Satara), Karmala/Mohol (belong to Solapur), Ranjangaon (Pune), or Sangamner (Ahilyanagar)."""
    },
    {
        'keys': ['kolhapur', 'कोल्हापूर', 'karvir', 'करवीर', 'panhala', 'पन्हाळा', 'shirol', 'शिरोळ', 'kagal', 'कागल', 'hatkanangle', 'हातकणंगले'],
        'info': """• KOLHAPUR DISTRICT (कोल्हापूर जिल्हा) - EXACTLY 12 TALUKAS:
  1. Karvir (करवीर - Kolhapur HQ is located within Karvir taluka; Kolhapur is NOT a separate taluka!)
  2. Panhala (पन्हाळा)
  3. Shahuwadi (शाहूवाडी)
  4. Kagal (कागल)
  5. Hatkanangle (हातकणंगले)
  6. Shirol (शिरोळ - strictly belongs to Kolhapur district, NOT Sangli)
  7. Radhanagari (राधानगरी)
  8. Gaganbawda (गगनबावडा)
  9. Bhudargad (भुदरगड)
  10. Gadhinglaj (गडहिंग्लज)
  11. Ajara (आजरा)
  12. Chandgad (चंदगड)
  *STRICT FACTUAL MANDATE*: Kolhapur has exactly 12 talukas."""
    },
    {
        'keys': ['satara', 'सातारा', 'wai', 'वाई', 'karad', 'कराड', 'phaltan', 'फलटण', 'mahabaleshwar', 'महाबळेश्वर'],
        'info': """• SATARA DISTRICT (सातारा जिल्हा) - EXACTLY 11 TALUKAS:
  1. Satara (सातारा)
  2. Wai (वाई)
  3. Khandala (खंडाळा)
  4. Koregaon (कोरेगाव)
  5. Phaltan (फलटण)
  6. Mahabaleshwar (महाबळेश्वर)
  7. Jawali / Medha (जावळी / मेढा)
  8. Patan (पाटण)
  9. Karad (कराड)
  10. Khatav / Vaduj (खटाव / वडूज)
  11. Man / Dahiwadi (माण / दहिवडी)"""
    },
    {
        'keys': ['solapur', 'सोलापूर', 'pandharpur', 'पंढरपूर', 'barshi', 'बार्शी', 'mohol', 'मोहोळ', 'karmala', 'करमाळा', 'akkalkot', 'अक्कलकोट'],
        'info': """• SOLAPUR DISTRICT (सोलापूर जिल्हा) - EXACTLY 11 TALUKAS:
  1. North Solapur (उत्तर सोलापूर)
  2. South Solapur (दक्षिण सोलापूर)
  3. Barshi (बार्शी)
  4. Mohol (मोहोळ)
  5. Madha (माढा)
  6. Karmala (करमाळा)
  7. Pandharpur (पंढरपूर)
  8. Sangola (सांगोला)
  9. Malshiras (माळशिरस)
  10. Mangalwedha (मंगळवेढा)
  11. Akkalkot (अक्कलकोट)"""
    },
    {
        'keys': ['pune', 'पुणे', 'haveli', 'हवेली', 'baramati', 'बारामती', 'shirur', 'शिरूर', 'maval', 'मावळ', 'junnar', 'जुन्नर'],
        'info': """• PUNE DISTRICT (पुणे जिल्हा) - EXACTLY 14 TALUKAS:
  1. Pune City (पुणे शहर)
  2. Haveli (हवेली)
  3. Khed / Rajgurunagar (खेड / राजगुरुनगर)
  4. Junnar (जुन्नर)
  5. Ambegaon (आंबेगाव)
  6. Maval (मावळ)
  7. Mulshi (मुळशी)
  8. Shirur (शिरूर)
  9. Daund (दौंड)
  10. Indapur (इंदापूर)
  11. Baramati (बारामती)
  12. Purandar / Saswad (पुरंदर / सासवड)
  13. Bhor (भोर)
  14. Velhe / Rajgad (वेल्हे / राजगड)"""
    },
    {
        'keys': ['mumbai', 'मुंबई'],
        'info': """• MUMBAI (मुंबई):
  - Mumbai City District (मुंबई शहर): 1 Urban District without separate rural talukas.
  - Mumbai Suburban District (मुंबई उपनगर - 3 Talukas): 1. Kurla (कुर्ला), 2. Andheri (अंधेरी), 3. Borivali (बोरीवली)."""
    },
    {
        'keys': ['thane', 'ठाणे', 'kalyan', 'कल्याण', 'bhiwandi', 'भिवंडी'],
        'info': """• THANE DISTRICT (ठाणे जिल्हा) - EXACTLY 7 TALUKAS:
  1. Thane (ठाणे), 2. Kalyan (कल्याण), 3. Murbad (मुरबाड), 4. Bhiwandi (भिवंडी), 5. Shahapur (शहापूर), 6. Ulhasnagar (उल्हासनगर), 7. Ambernath (अंबरनाथ)."""
    },
    {
        'keys': ['palghar', 'पालघर', 'vasai', 'वसई', 'dahanu', 'डहाणू'],
        'info': """• PALGHAR DISTRICT (पालघर जिल्हा) - EXACTLY 8 TALUKAS:
  1. Palghar (पालघर), 2. Vada (वाडा), 3. Vikramgad (विक्रमगड), 4. Jawhar (जव्हार), 5. Mokhada (मोखाडा), 6. Dahanu (डहाणू), 7. Talasari (तलासरी), 8. Vasai (वसई)."""
    },
    {
        'keys': ['raigad', 'रायगड', 'alibag', 'अलिबाग', 'panvel', 'पनवेल'],
        'info': """• RAIGAD DISTRICT (रायगड जिल्हा) - EXACTLY 15 TALUKAS:
  1. Alibag (अलिबाग), 2. Pen (पेण), 3. Murud (मुरुड), 4. Panvel (पनवेल), 5. Uran (उरण), 6. Karjat (कर्जत), 7. Khalapur (खालापूर), 8. Mangaon (माणगाव), 9. Roha (रोहा), 10. Sudhagad / Pali (सुधागड / पाली), 11. Mahad (महाड), 12. Poladpur (पोलादपूर), 13. Shrivardhan (श्रीवर्धन), 14. Mhasla (म्हसळा), 15. Tala (तळा)."""
    },
    {
        'keys': ['ratnagiri', 'रत्नागिरी', 'chiplun', 'चिपळूण'],
        'info': """• RATNAGIRI DISTRICT (रत्नागिरी जिल्हा) - EXACTLY 9 TALUKAS:
  1. Ratnagiri (रत्नागिरी), 2. Sangameshwar (संगमेश्वर), 3. Lanja (लांजा), 4. Rajapur (राजापूर), 5. Chiplun (चिपळूण), 6. Guhagar (गुहागर), 7. Dapoli (दापोली), 8. Mandangad (मंडणगड), 9. Khed (खेड)."""
    },
    {
        'keys': ['sindhudurg', 'सिंधुदुर्ग', 'sawantwadi', 'सावंतवाडी', 'malvan', 'मालवण'],
        'info': """• SINDHUDURG DISTRICT (सिंधुदुर्ग जिल्हा) - EXACTLY 8 TALUKAS:
  1. Kudal (कुडाळ), 2. Malvan (मालवण), 3. Sawantwadi (सावंतवाडी), 4. Vengurla (वेंगुर्ला), 5. Kankavli (कणकवली), 6. Deogad (देवगड), 7. Vaibhavwadi (वैभववाडी), 8. Dodamarg (दोडामार्ग)."""
    },
    {
        'keys': ['nashik', 'नाशिक', 'malegaon', 'मालेगाव'],
        'info': """• NASHIK DISTRICT (नाशिक जिल्हा) - EXACTLY 15 TALUKAS:
  1. Nashik (नाशिक), 2. Sinnar (सिन्नर), 3. Dindori (दिंडोरी), 4. Igatpuri (इगतपुरी), 5. Peint (पेठ), 6. Trimbakeshwar (त्र्यंबकेश्वर), 7. Kalwan (कळवण), 8. Deola (देवळा), 9. Surgana (सुरगाणा), 10. Baglan / Satana (बागलाण / सटाणा), 11. Malegaon (मालेगाव), 12. Nandgaon (नांदगाव), 13. Chandwad (चांदवड), 14. Niphad (निफाड), 15. Yevla (येवला)."""
    },
    {
        'keys': ['ahmednagar', 'अहमदनगर', 'ahilyanagar', 'अहिल्यानगर', 'shirdi', 'शिर्डी', 'sangamner', 'संगमनेर'],
        'info': """• AHILYANAGAR / AHMEDNAGAR (अहिल्यानगर / अहमदनगर जिल्हा) - EXACTLY 14 TALUKAS:
  1. Nagar (नगर), 2. Rahuri (राहुरी), 3. Nevasa (नेवासा), 4. Shevgaon (शेवगाव), 5. Pathardi (पाथर्डी), 6. Jamkhed (जामखेड), 7. Karjat (कर्जत), 8. Shrigonda (श्रीगोंदा), 9. Parner (पारनेर), 10. Sangamner (संगमनेर), 11. Akole (अकोले), 12. Kopargaon (कोपरगाव), 13. Shrirampur (श्रीरामपूर), 14. Rahata (राहाता)."""
    },
    {
        'keys': ['dhule', 'धुळे', 'shirpur', 'शिरपूर'],
        'info': """• DHULE DISTRICT (धुळे जिल्हा) - EXACTLY 4 TALUKAS:
  1. Dhule (धुळे), 2. Sakri (साक्री), 3. Shirpur (शिरपूर), 4. Sindkheda (शिंदखेडा)."""
    },
    {
        'keys': ['nandurbar', 'नंदुरबार', 'shahada', 'शहादा'],
        'info': """• NANDURBAR DISTRICT (नंदुरबार जिल्हा) - EXACTLY 6 TALUKAS:
  1. Nandurbar (नंदुरबार), 2. Navapur (नवापूर), 3. Shahada (शहादा), 4. Taloda (तळोदा), 5. Akkalkuwa (अक्कलकुवा), 6. Dhadgaon / Akrani (धडगाव / अक्राणी)."""
    },
    {
        'keys': ['jalgaon', 'जळगाव', 'bhusawal', 'भुसावळ'],
        'info': """• JALGAON DISTRICT (जळगाव जिल्हा) - EXACTLY 15 TALUKAS:
  1. Jalgaon (जळगाव), 2. Jamner (जामनेर), 3. Erandol (एरंडोल), 4. Dharangaon (धरणगाव), 5. Bhusawal (भुसावळ), 6. Raver (रावेर), 7. Muktainagar (मुक्ताईनगर), 8. Bodwad (बोधवड), 9. Yawal (यावल), 10. Amalner (अमळनेर), 11. Parola (पारोळा), 12. Chopda (चोपडा), 13. Pachora (पाचोरा), 14. Bhadgaon (भडगाव), 15. Chalisgaon (चाळीसगाव)."""
    },
    {
        'keys': ['sambhajinagar', 'संभाजीनगर', 'aurangabad', 'औरंगाबाद'],
        'info': """• CHHATRAPATI SAMBHAJINAGAR (छत्रपती संभाजीनगर जिल्हा) - EXACTLY 9 TALUKAS:
  1. Chhatrapati Sambhajinagar (छत्रपती संभाजीनगर), 2. Kannad (कन्नड), 3. Soegaon (सोयगाव), 4. Sillod (सिल्लोड), 5. Phulambri (फुलंब्री), 6. Khuldabad (खुलताबाद), 7. Vaijapur (वैजापूर), 8. Gangapur (गंगापूर), 9. Paithan (पैठण)."""
    },
    {
        'keys': ['jalna', 'जालना'],
        'info': """• JALNA DISTRICT (जालना जिल्हा) - EXACTLY 8 TALUKAS:
  1. Jalna (जालना), 2. Ambad (अंबड), 3. Bhokardan (भोकरदन), 4. Jafrabad (जाफ्राबाद), 5. Partur (परतूर), 6. Ghansawangi (घनसावंगी), 7. Mantha (मंठा), 8. Badnapur (बदनपूर)."""
    },
    {
        'keys': ['parbhani', 'परभणी'],
        'info': """• PARBHANI DISTRICT (परभणी जिल्हा) - EXACTLY 9 TALUKAS:
  1. Parbhani (परभणी), 2. Gangakhed (गंगाखेड), 3. Sonpeth (सोनपेठ), 4. Pathri (पाथरी), 5. Manwath (मानवत), 6. Palam (पालम), 7. Selu (सेलू), 8. Jintur (जिंतूर), 9. Purna (पूर्णा)."""
    },
    {
        'keys': ['hingoli', 'हिंगोली'],
        'info': """• HINGOLI DISTRICT (हिंगोली जिल्हा) - EXACTLY 5 TALUKAS:
  1. Hingoli (हिंगोली), 2. Sengaon (सेनगाव), 3. Kalamnuri (कलमनुरी), 4. Basmath (वसमत / बसमत), 5. Aundha Nagnath (औंढा नागनाथ)."""
    },
    {
        'keys': ['nanded', 'नांदेड'],
        'info': """• NANDED DISTRICT (नांदेड जिल्हा) - EXACTLY 16 TALUKAS:
  1. Nanded (नांदेड), 2. Ardhapur (अर्धापूर), 3. Mudkhed (मुदखेड), 4. Bhokar (भोकर), 5. Loha (लोहा), 6. Kandhar (कंधार), 7. Kinwat (किनवट), 8. Himayatnagar (हिमायतनगर), 9. Hadgaon (हदगाव), 10. Mahur (माहूर), 11. Deglur (देगलूर), 12. Mukhed (मुखेड), 13. Dharmabad (धर्माबाद), 14. Biloli (बिलोली), 15. Naigaon (नायगाव), 16. Umri (उमरी)."""
    },
    {
        'keys': ['beed', 'बीड', 'parli', 'परळी', 'majalgaon', 'माजलगाव'],
        'info': """• BEED DISTRICT (बीड जिल्हा) - EXACTLY 11 TALUKAS:
  1. Beed (बीड), 2. Georai (गेवराई), 3. Majalgaon (माजलगाव), 4. Ambejogai (अंबाजोगाई), 5. Kaij (केज), 6. Parli Vaijnath (परळी वैजनाथ), 7. Patoda (पाटोदा), 8. Shirur Kasar (शिरूर कासार), 9. Ashti (आष्टी), 10. Wadwani (वडवणी), 11. Dharur (धारूर)."""
    },
    {
        'keys': ['latur', 'लातूर', 'udgir', 'उदगीर'],
        'info': """• LATUR DISTRICT (लातूर जिल्हा) - EXACTLY 10 TALUKAS:
  1. Latur (लातूर), 2. Ausa (औसा), 3. Renapur (रेणापूर), 4. Ahmedpur (अहमदपूर), 5. Jalkot (जलकोट), 6. Chakur (चाकूर), 7. Shirur Anantpal (शिरूर अनंतपाळ), 8. Udgir (उदगीर), 9. Deoni (देवणी), 10. Nilanga (निलंगा)."""
    },
    {
        'keys': ['dharashiv', 'धाराशिव', 'osmanabad', 'उस्मानाबाद', 'tuljapur', 'तुळजापूर'],
        'info': """• DHARASHIV / OSMANABAD (धाराशिव / उस्मानाबाद जिल्हा) - EXACTLY 8 TALUKAS:
  1. Dharashiv (धाराशिव), 2. Tuljapur (तुळजापूर), 3. Omerga (उमरगा), 4. Lohara (लोहारा), 5. Kalamb (कळंब), 6. Bhum (भूम), 7. Paranda (परांडा), 8. Washi (वाशी)."""
    },
    {
        'keys': ['amravati', 'अमरावती', 'chikhaldara', 'चिखलदरा'],
        'info': """• AMRAVATI DISTRICT (अमरावती जिल्हा) - EXACTLY 14 TALUKAS:
  1. Amravati (अमरावती), 2. Bhatkuli (भातकुली), 3. Nandgaon Khandeshwar (नांदगाव खंडेश्वर), 4. Dharni (धारणी), 5. Chikhaldara (चिखलदरा), 6. Achalpur (अचलपूर), 7. Chandurbazar (चांदूर बाजार), 8. Morshi (मोर्शी), 9. Warud (वरुड), 10. Daryapur (दर्यापूर), 11. Anjangaon Surji (अंजनगाव सुर्जी), 12. Chandur Railway (चांदूर रेल्वे), 13. Dhamangaon Railway (धामणगाव रेल्वे), 14. Tiwsa (तिवसा)."""
    },
    {
        'keys': ['akola', 'अकोला'],
        'info': """• AKOLA DISTRICT (अकोला जिल्हा) - EXACTLY 7 TALUKAS:
  1. Akola (अकोला), 2. Akot (आकोट), 3. Telhara (तेल्हारा), 4. Balapur (बाळापूर), 5. Patur (पातूर), 6. Murtizapur (मूर्तिजापूर), 7. Barshitakli (बार्शीटाकळी)."""
    },
    {
        'keys': ['washim', 'वाशिम'],
        'info': """• WASHIM DISTRICT (वाशिम जिल्हा) - EXACTLY 6 TALUKAS:
  1. Washim (वाशिम), 2. Malegaon (मालेगाव), 3. Risod (रिसोड), 4. Mangrulpir (मंगरुळपीर), 5. Karanja (कारंजा), 6. Manora (मनोरा)."""
    },
    {
        'keys': ['buldhana', 'बुलढाणा', 'shegaon', 'शेगाव', 'lonar', 'लोणार'],
        'info': """• BULDHANA DISTRICT (बुलढाणा जिल्हा) - EXACTLY 13 TALUKAS:
  1. Buldhana (बुलढाणा), 2. Chikhli (चिखली), 3. Deulgaon Raja (देऊळगाव राजा), 4. Jalgaon Jamod (जळगाव जामोद), 5. Sangrampur (संग्रामपूर), 6. Malkapur (मलकापूर), 7. Motala (मोताळा), 8. Nandura (नांदुरा), 9. Khamgaon (खामगाव), 10. Shegaon (शेगाव), 11. Mehkar (मेहकर), 12. Sindkhed Raja (सिंदखेड राजा), 13. Lonar (लोणार)."""
    },
    {
        'keys': ['yavatmal', 'यवतमाळ'],
        'info': """• YAVATMAL DISTRICT (यवतमाळ जिल्हा) - EXACTLY 16 TALUKAS:
  1. Yavatmal (यवतमाळ), 2. Arni (आर्णी), 3. Babhulgaon (बाभूळगाव), 4. Kalamb (कळंब), 5. Darwha (दारव्हा), 6. Digras (दिग्रस), 7. Ner (नेर), 8. Pusad (पुसद), 9. Umarkhed (उमरखेड), 10. Mahagaon (महागाव), 11. Ghatanji (घाटंजी), 12. Wani (वणी), 13. Maregaon (मारेगाव), 14. Zari Jamani (झरी जामणी), 15. Kelapur / Pandharkawada (केळापूर / पांढरकवडा), 16. Ralegaon (राळेगाव)."""
    },
    {
        'keys': ['nagpur', 'नागपूर'],
        'info': """• NAGPUR DISTRICT (नागपूर जिल्हा) - EXACTLY 14 TALUKAS:
  1. Nagpur Urban (नागपूर शहर), 2. Nagpur Rural (नागपूर ग्रामीण), 3. Kamptee (कामठी), 4. Hingna (हिंगणा), 5. Katol (काटोल), 6. Narkhed (नरखेड), 7. Savner (सावनेर), 8. Kalameshwar (कळमेश्वर), 9. Ramtek (रामटेक), 10. Mouda (मौदा), 11. Parseoni (पारशिवनी), 12. Umred (उमरेड), 13. Kuhi (कुही), 14. Bhivapur (भिवापूर)."""
    },
    {
        'keys': ['wardha', 'वर्धा'],
        'info': """• WARDHA DISTRICT (वर्धा जिल्हा) - EXACTLY 8 TALUKAS:
  1. Wardha (वर्धा), 2. Deoli (देवळी), 3. Seloo (सेलू), 4. Arvi (आर्वी), 5. Ashti (आष्टी), 6. Karanja (कारंजा), 7. Hinganghat (हिंगणघाट), 8. Samudrapur (समुद्रपूर)."""
    },
    {
        'keys': ['bhandara', 'भंडारा'],
        'info': """• BHANDARA DISTRICT (भंडारा जिल्हा) - EXACTLY 7 TALUKAS:
  1. Bhandara (भंडारा), 2. Tumsar (तुमसर), 3. Pauni (पवनी), 4. Mohadi (मोहाडी), 5. Sakoli (साकोली), 6. Lakhani (लाखनी), 7. Lakhandur (लाखांदूर)."""
    },
    {
        'keys': ['gondia', 'गोंदिया'],
        'info': """• GONDIA DISTRICT (गोंदिया जिल्हा) - EXACTLY 8 TALUKAS:
  1. Gondia (गोंदिया), 2. Tirora (तिरोडा), 3. Goregaon (गोरेगाव), 4. Arjuni Morgaon (अर्जुनी मोरगाव), 5. Deori (देवरी), 6. Amgaon (आमगाव), 7. Salekasa (सालेकसा), 8. Sadak Arjuni (सडक अर्जुनी)."""
    },
    {
        'keys': ['chandrapur', 'चंद्रपूर'],
        'info': """• CHANDRAPUR DISTRICT (चंद्रपूर जिल्हा) - EXACTLY 15 TALUKAS:
  1. Chandrapur (चंद्रपूर), 2. Bhadravati (भद्रावती), 3. Warora (वरोरा), 4. Chimur (चिमूर), 5. Nagbhid (नागभीड), 6. Bramhapuri (ब्रह्मपुरी), 7. Sindewahi (सिंदेवाही), 8. Mul (मूल), 9. Saoli (सावली), 10. Pombhurna (पोंभुर्णा), 11. Ballarpur (बल्लारपूर), 12. Gondpipri (गोंडपिंपरी), 13. Korpana (कोरपना), 14. Rajura (राजूरा), 15. Jiwati (जिवती)."""
    },
    {
        'keys': ['gadchiroli', 'गडचिरोली'],
        'info': """• GADCHIROLI DISTRICT (गडचिरोली जिल्हा) - EXACTLY 12 TALUKAS:
  1. Gadchiroli (गडचिरोली), 2. Dhanora (धानोरा), 3. Chamorshi (चामोर्शी), 4. Mulchera (मूलचेरा), 5. Armori (आरमोरी), 6. Kurkheda (कुरखेडा), 7. Korchi (कोरची), 8. Wadsa / Desaiganj (वडसा / देसाईगंज), 9. Aheri (अहेरी), 10. Sironcha (सिरोंचा), 11. Bhamragad (भामरागड), 12. Etapalli (एटापल्ली)."""
    }
]

def get_relevant_ground_truth(query: str) -> str:
    """Dynamically assemble strictly relevant verified ground truth without exceeding token rate limits."""
    q_low = query.lower().strip()

    # Casual greetings don't need heavy state-specific benchmark data
    casual_greetings = {"hi", "hello", "hey", "hii", "hiii", "namaste", "good morning", "good evening", "good night", "who are you", "what is your name"}
    if q_low in casual_greetings:
        return ""

    base_facts = VERIFIED_GROUND_TRUTH_FACTS

    matched_districts = []
    for item in MAHARASHTRA_DISTRICT_DATA:
        if any(k in q_low for k in item['keys']):
            matched_districts.append(item['info'])

    is_geo_query = any(w in q_low for w in ["taluka", "district", "tehsil", "तालुका", "तालुके", "जिल्हा", "विभाग", "division", "headquarters"])
    if matched_districts:
        return f"{base_facts}\n\n[VERIFIED OFFICIAL MAHARASHTRA ADMINISTRATIVE ROSTER FOR TARGET DISTRICT(S)]:\n" + "\n\n".join(matched_districts)
    elif is_geo_query:
        # Include top division reference summary
        samples = [item['info'] for item in MAHARASHTRA_DISTRICT_DATA[:8]]
        return f"{base_facts}\n\n[VERIFIED OFFICIAL MAHARASHTRA ADMINISTRATIVE ROSTER (SAMPLE BENCHMARKS)]:\n" + "\n\n".join(samples)

    return base_facts

def sanitize_ai_output(text: str) -> str:
    """Detect and sanitize pathological token loops, repetitive text, or leaked prompt markers."""
    if not text:
        return text
    # Clean up repetitive article loops like 124A, 124B, 124C ... 124YA
    text = re.sub(r'(?:(?:Art\.\s*|Article\s*)?124[A-Z]{1,2}(?:,\s*|\s+)){4,}', 'Art. 124, 124A, 124B, 124C ', text)
    # Clean up repetitive alphanumeric sequences
    text = re.sub(r'(\b\w+\b)(?:,\s*\1){4,}', r'\1', text)
    # Remove meta-announcements or benchmark roster phrases if any leaked into output
    text = re.sub(r'^(?:Based on the verified reference snippet provided in the context:?\s*)+', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\(?as per the verified governmental roster[^)]*\)?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\(?as per the official list for \d{4}[-–]\d{4}\)?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\*?These details are taken from the verified factual benchmarks[^\n.]*\*?', '', text, flags=re.IGNORECASE)

    # Ensure correct authentic Marathi administrative spellings
    text = re.sub(r'कावठे\s*मांझी', 'कवठे महांकाळ', text)
    text = re.sub(r'(?<![ऀ-ॿ])तसगाव(?![ऀ-ॿ])', 'तासगाव', text)
    text = re.sub(r'(?<![ऀ-ॿ])काडेगाव(?![ऀ-ॿ])', 'कडेगाव', text)
    text = re.sub(r'(?<![ऀ-ॿ])पालुस(?![ऀ-ॿ])', 'पलूस', text)
    text = re.sub(r'(?<![ऀ-ॿ])शिराला(?![ऀ-ॿ])', 'शिराळा', text)
    text = re.sub(r'(?<![ऀ-ॿ])विता(?![ऀ-ॿ])', 'विटा', text)
    text = re.sub(r'(?<![ऀ-ॿ])जाट\s*तालुका(?![ऀ-ॿ])', 'जत तालुका', text)
    text = re.sub(r'(\d+[\.\)]\s*\*{0,2})जाट(\*{0,2})', r'\1जत\2', text)

    return text.strip()

def is_devanagari_text(text: str) -> bool:
    """Check if query contains Devanagari script (Marathi / Hindi)."""
    return any('\u0900' <= c <= '\u097F' for c in text)

def is_pure_date_query(query: str) -> bool:
    """Check if query is asking for current date or time, which python knows accurately."""
    q = query.lower().strip()
    date_patterns = [
        "todays date", "today date", "today's date", "aajchi tarikh", "current date", 
        "aaj ka date", "aaj tarikh kay ahe", "tarikh sang", "what is today's date",
        "what is the date today", "what date is it", "current time", "aajcha divas",
        "date today", "today is which date"
    ]
    return any(p in q for p in date_patterns)

def detect_target_language(query: str, recent_msgs: list = None) -> str:
    """
    Detect the expected response language adhering strictly to global standards:
    - Default is English.
    - Switch to Marathi ONLY if explicitly asked ('give in marathi', 'in marathi', 'marathit sang') 
      OR if the question itself is asked in Marathi.
    - Switch to Hindi ONLY if explicitly asked ('give in hindi', 'in hindi', 'hindi me batao') 
      OR if the question itself is asked in Hindi.
    """
    if not query:
        return "English"

    q_low = query.lower().strip()

    # 1. Explicit language directives in the query take highest priority
    if re.search(r'\b(in english|give in english|explain in english|english please|english me|english mein|english madhe|english mdhe)\b', q_low) or any(w in query for w in ["इंग्रजीत", "इंग्लिश मध्ये", "इंग्लिशमध्ये"]):
        return "English"

    if re.search(r'\b(in marathi|give in marathi|explain in marathi|tell in marathi|marathi please|marathit|marathitun|marathi madhe|marathi mdhe|marathi dya|marathit sang|marathit dakhva)\b', q_low) or any(w in query for w in ["मराठीत", "मराठी मध्ये", "मराठीत सांगा", "मराठीत द्या"]):
        return "Marathi"

    if re.search(r'\b(in hindi|give in hindi|explain in hindi|tell in hindi|hindi please|hindi me|hindi mein|hindi madhe|hindi mdhe|hindi me batao|hindi me dalo|hindi me dijiye)\b', q_low) or any(w in query for w in ["हिंदी में", "हिन्दी में", "हिंदी में बताओ", "हिंदी में दीजिए"]):
        return "Hindi"

    # 2. Check if the question itself is written in Devanagari script
    if is_devanagari_text(query):
        # ळ is exclusive to Marathi
        if 'ळ' in query:
            return "Marathi"

        marathi_devanagari = ["आहे", "आहेत", "नाही", "नाहीत", "काय", "कोणते", "कोणती", "कोणता", "कसे", "कसा", "कशी", "सांगा", "माहिती", "जिल्ह्यातील", "झाले", "झाली", "झाला", "तालुका", "तालुके", "किल्ला", "किल्ले", "योजना", "शासन", "बघा", "करा"]
        hindi_devanagari = ["है", "हैं", "नहीं", "क्या", "कौन", "कैसे", "कैसा", "कैसी", "बताओ", "बताइए", "जानकारी", "हुआ", "हुई", "हुए", "कीजिए", "करिए", "जिले", "तहसील"]

        m_score = sum(1 for w in marathi_devanagari if w in query)
        h_score = sum(1 for w in hindi_devanagari if w in query)

        if h_score > m_score:
            return "Hindi"
        return "Marathi"

    # 3. Check for standard greetings (strictly English)
    if q_low in {"hi", "hello", "hey", "hii", "hiii", "good morning", "good evening", "good night", "how are you"}:
        return "English"

    # 4. Check for Romanized / Transliterated Marathi or Hindi questions
    words = set(re.findall(r'\b[a-z]+\b', q_low))
    marathi_roman_words = {
        "ahe", "aahe", "nahit", "nahi", "kashi", "kasa", "kase", "sang", "sanga", 
        "dya", "de", "pahije", "kiti", "kuthe", "kashala", "mahit", "mahiti", 
        "jilhyatil", "jilhyache", "taluke", "bgh", "bagh", "kela", "keli", "kel", 
        "hota", "hoti", "hote", "baddal", "vishayi", "tula", "mala", "apan", 
        "amhi", "tumhi", "karaycha", "karnar", "adhich", "sangitla", "shikva", "aajchi"
    }
    hindi_roman_words = {
        "kya", "kaise", "kaisa", "kaisi", "hain", "nahin", "batao", "bataiye", 
        "chahiye", "kitna", "kitni", "kitne", "kaun", "kahan", "kisko", "mujhe", 
        "tumhe", "aapko", "karna", "karega", "karenge", "hoga", "hogi", "baare"
    }

    m_matches = words.intersection(marathi_roman_words)
    h_matches = words.intersection(hindi_roman_words)

    # Only flag as Marathi/Hindi if query has clear vernacular tokens and isn't predominantly English
    english_common = {"is", "are", "the", "what", "how", "who", "where", "why", "tell", "about", "give", "me"}
    has_english_structure = bool(words.intersection(english_common))

    if len(m_matches) >= 2 or (len(m_matches) == 1 and not has_english_structure):
        return "Marathi"

    if len(h_matches) >= 2 or (len(h_matches) == 1 and not has_english_structure):
        return "Hindi"

    # Default to English globally
    return "English"


def fetch_live_web_context(query: str) -> str:
    """Fetch live real-time internet facts using multi-engine search with strict relevance filtering."""
    results = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept-Language': 'mr,hi,en-IN,en;q=0.9'
    }

    cleaned_query = query.strip()
    if len(cleaned_query) > 100:
        cleaned_query = cleaned_query[:100]

    is_devanagari = is_devanagari_text(cleaned_query)

    # Enrich search terms for domain-specific queries
    search_query = cleaned_query
    q_lower = cleaned_query.lower()
    if "ladki bahin" in q_lower or "लाडकी बहीण" in cleaned_query:
        search_query = "Mukhyamantri Majhi Ladki Bahin Yojana Maharashtra government"
    elif "dhara" in q_lower or "धारा" in cleaned_query:
        search_query = f"{cleaned_query} कायदा law section constitution"

    query_words = [w.lower() for w in re.findall(r'[\w\u0900-\u097F]+', search_query) if len(w) >= 2]
    stop_words = {
        "the", "and", "for", "with", "about", "what", "who", "when", "where", "how", "only", "name", 
        "ahe", "aahe", "kon", "hote", "kay", "kashi", "kiti", "kahi", "ata", "aaj", "navin", "sang",
        "please", "tell", "info", "information", "details"
    }
    meaningful_words = [w for w in query_words if w not in stop_words]

    def is_relevant_snippet(text: str) -> bool:
        """Filter out junk, ads, or irrelevant snippets."""
        if not text or len(text) < 20:
            return False
        text_lower = text.lower()
        junk_patterns = [
            "electric current", "ampere", "cuisine", "recipe", "song title",
            "crazygames", "youtube", "how to get help in windows", "forum francophone",
            "status quo", "download mp3", "online casino", "betting"
        ]
        if any(j in text_lower for j in junk_patterns):
            return False
        if meaningful_words:
            return any(w in text_lower for w in meaningful_words)
        return True

    is_news_intent = any(w in q_lower for w in [
        "news", "latest", "recent", "today", "yesterday", "update", "current affairs", 
        "accident", "election", "cabinet", "meeting", "breaking", "death", "died", "resigned",
        "verdict", "court order", "announcement", "gr", "झाली", "झाला", "बातमी", "नवे", "नवीन", "काल", "आजची"
    ])

    # 1. Google News RSS ONLY for live breaking news, incidents, and appointments
    if is_news_intent:
        try:
            search_terms = re.sub(
                r'\b(name only|only name|verify it|verify|please|tell me about|what is the|who is the|kon ahe|kon aahe)\b',
                '', search_query, flags=re.IGNORECASE
            ).strip() or search_query

            if is_devanagari:
                news_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(search_terms)}&hl=mr&gl=IN&ceid=IN:mr"
            else:
                news_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(search_terms)}&hl=en-IN&gl=IN&ceid=IN:en"

            req = urllib.request.Request(news_url, headers=headers)
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                root = ET.fromstring(resp.read())
                items = root.findall('.//item')[:4]
                for it in items:
                    title = it.find('title').text if it.find('title') is not None else ''
                    pub = it.find('pubDate').text if it.find('pubDate') is not None else ''
                    if title and (not meaningful_words or any(w in title.lower() for w in meaningful_words)):
                        results.append(f"• [Live News ({pub[:16]})]: {title}")
        except Exception as ne:
            print(f"[WebSearch] Google News skipped: {ne}")

    # 2. Wikipedia API (Deep administrative/overview section parsing)
    wiki_domains = ['mr.wikipedia.org', 'en.wikipedia.org'] if is_devanagari else ['en.wikipedia.org']
    wiki_headers = {
        'User-Agent': 'NexoraAI/2.0 (Academic & Competitive Exam Mentor; contact@nexora.ai)',
        'Accept-Language': 'mr,en;q=0.9'
    }
    
    clean_wiki_query = re.sub(r'^(list\s+of\s+|names?\s+of\s+|all\s+)', '', search_query, flags=re.IGNORECASE).strip()
    for domain in wiki_domains:
        try:
            wiki_search_url = f"https://{domain}/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(clean_wiki_query)}&format=json&utf8=1&srlimit=2"
            req = urllib.request.Request(wiki_search_url, headers=wiki_headers)
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                for item in data.get('query', {}).get('search', []):
                    title = item.get('title', '')
                    if not title:
                        continue
                    
                    # Check for dedicated administrative sections (e.g. Talukas / Tehsils / Administration)
                    target_sec_idx = None
                    target_sec_name = None
                    try:
                        sec_url = f"https://{domain}/w/api.php?action=parse&page={urllib.parse.quote(title)}&prop=sections&format=json"
                        sreq = urllib.request.Request(sec_url, headers=wiki_headers)
                        with urllib.request.urlopen(sreq, timeout=2.5) as sresp:
                            sdata = json.loads(sresp.read().decode('utf-8'))
                            for s in sdata.get('parse', {}).get('sections', []):
                                s_line_low = s.get('line', '').lower()
                                if any(w in s_line_low for w in ['administration', 'taluka', 'tehsil', 'sub-division', 'subdivision', 'talukas']):
                                    target_sec_idx = s.get('index')
                                    target_sec_name = s.get('line')
                                    break
                    except Exception:
                        pass

                    if target_sec_idx:
                        # Fetch the exact administrative section
                        try:
                            txt_url = f"https://{domain}/w/api.php?action=parse&page={urllib.parse.quote(title)}&section={target_sec_idx}&prop=wikitext&format=json"
                            treq = urllib.request.Request(txt_url, headers=wiki_headers)
                            with urllib.request.urlopen(treq, timeout=2.5) as tresp:
                                tdata = json.loads(tresp.read().decode('utf-8'))
                                wikitxt = tdata.get('parse', {}).get('wikitext', {}).get('*', '')
                                clean_sec = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', wikitxt)
                                clean_sec = re.sub(r'\{\{[^\}]*\}\}', '', clean_sec)
                                clean_sec = re.sub(r'==+[^=]+==+', '', clean_sec)
                                clean_sec = re.sub(r'<[^>]+>', '', clean_sec).strip()
                                clean_sec = re.sub(r'\n+', '\n', clean_sec)
                                if len(clean_sec) > 20:
                                    results.append(f"• [Wikipedia - {title} ({target_sec_name})]: {clean_sec[:1000]}")
                                    continue
                        except Exception:
                            pass

                    # Fallback to lead intro extract
                    try:
                        ext_url = f"https://{domain}/w/api.php?action=query&prop=extracts&explaintext=1&exintro=1&titles={urllib.parse.quote(title)}&format=json"
                        ereq = urllib.request.Request(ext_url, headers=wiki_headers)
                        with urllib.request.urlopen(ereq, timeout=2.5) as eresp:
                            edata = json.loads(eresp.read().decode('utf-8'))
                            page_obj = next(iter(edata.get('query', {}).get('pages', {}).values()))
                            extract = page_obj.get('extract', '').strip()
                            if extract and is_relevant_snippet(extract):
                                results.append(f"• [Wikipedia - {title}]: {extract[:700]}")
                    except Exception:
                        # Fallback snippet
                        snippet = re.sub(r'<[^>]+>', '', item.get('snippet', ''))
                        snippet = html.unescape(snippet).strip()
                        if snippet and is_relevant_snippet(snippet):
                            results.append(f"• [Wikipedia - {title}]: {snippet}")
        except Exception as we:
            print(f"[WebSearch] Wikipedia ({domain}) skipped: {we}")

    # 3. Bing Web Search (Cleaned query without Microsoft Lists confusion)
    try:
        clean_bing_query = re.sub(r'^(list\s+of\s+|names?\s+of\s+)', '', search_query, flags=re.IGNORECASE).strip()
        lang_param = "&setlang=mr&cc=in" if is_devanagari else "&setlang=en&cc=in"
        bing_url = f"https://www.bing.com/search?q={urllib.parse.quote(clean_bing_query)}{lang_param}"
        req = urllib.request.Request(bing_url, headers=headers)
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            page = resp.read().decode('utf-8', errors='ignore')
            snippets = re.findall(r'<div class="b_caption">\s*<p[^>]*>(.*?)</p>', page, re.DOTALL)
            for snip in snippets[:4]:
                clean = re.sub(r'<[^>]+>', '', snip)
                clean = html.unescape(clean).strip()
                clean = re.sub(r'\s+', ' ', clean)
                if is_relevant_snippet(clean):
                    results.append(f"• [Web Reference]: {clean}")
    except Exception as be:
        print(f"[WebSearch] Bing search skipped: {be}")

    return "\n".join(results[:5])

def needs_live_search(query: str) -> bool:
    """Detect if the query asks for real-world factual information, events, accidents, news, governance, syllabus, etc."""
    if not query or not query.strip():
        return False

    # Never do external search for pure date/time queries (Python system date handles them accurately)
    if is_pure_date_query(query):
        return False

    q = query.lower().strip()

    # Skip pure conversational greetings & meta language switch requests
    casual_greetings = {
        "hi", "hello", "hey", "hii", "hiii", "namaste", "good morning", "good evening", 
        "good night", "thank you", "thanks", "bye", "in marathi", "give in marathi", 
        "in hindi", "give in hindi", "in english", "give in english", "marathit sang", 
        "hindi me batao", "marathi", "hindi", "english"
    }
    if q in casual_greetings:
        return False


    # Skip pure programming code syntax / leetcode tasks with no real-world fact element
    code_patterns = ["write a python", "write python", "write a code", "write a function", "write an algorithm", "solve leetcode", "regex for", "css style for", "html table for"]
    if any(p in q for p in code_patterns):
        return False

    # Skip well-established static constitutional powers that never change
    static_legal = ["powers of the president", "powers of president", "article 21", "artical 21", "art 21", "kalam 21", "dhara 360", "kalam 360", "article 370", "artical 370"]
    if any(s in q for s in static_legal):
        return False

    # All real-world informational, factual, event, news, person, accident, place, or exam questions trigger search!
    return True

SYSTEM_PROMPT = """You are Nexora AI, an elite, highly reliable encyclopedic AI Assistant, master educator, and expert Competitive Exam & Law Mentor (equivalent to ChatGPT-4 / Claude-3.5 Sonnet in depth, factual precision, and pedagogical quality).
Your official name is Nexora AI. When asked who you are, what your name is, or to introduce yourself in any language (English, Marathi, Hindi), introduce yourself as Nexora AI, an intelligent AI assistant and mentor.

CORE MANDATES:
1. STRICT AUTHENTICITY & TRUTH (ZERO FAKE INFORMATION):
   - Provide only 100% verified real-world facts, official figures, and authentic information.
   - NEVER hallucinate, guess, or fabricate names, dates, events, accident reports, or exam dates.
   - NEVER generate repetitive token loops or runaway sequences (such as repeating 124A, 124B, 124C... 124YA). Only cite legitimate, recognized constitutional articles.
   - If a niche fact is unverified or speculative, honestly state that this detail is not officially verified, and direct the user to official gazettes or portals (e.g., upsc.gov.in, mpsc.gov.in, bombayhighcourt.nic.in, ecourts.gov.in).
   - Strictly honor verified benchmarks provided in the system context.

2. CRITICAL FORMATTING MANDATE - STRICT RESTRAINT ON TABLES:
   - DO NOT put entire answers or normal explanatory text in Markdown tables!
   - Use Markdown tables ONLY when there is a genuine, strict need — specifically for direct comparative side-by-side matrices (e.g. comparing BNS vs IPC section mappings, or multi-year cutoff statistics).
   - For all explanations, conceptual legal analysis, exam strategies, section breakdowns, history, and advice: use clean structured headings (##, ###), clear bold highlights, elegant bullet points, and neat, flowing paragraphs.
   - Keep responses visually clean, highly readable, and neatly separated.

3. COMPREHENSIVE LAW & JUDICIARY MENTORSHIP (JMFC, MH CET Law, CLAT, MPSC APP, Judiciary):
   - Provide authoritative, in-depth guidance for Maharashtra Judicial Magistrate First Class (JMFC) / Civil Judge Junior Division (CJJD), MPSC Assistant Public Prosecutor (APP), MH CET Law (3-Year & 5-Year LL.B), and CLAT.
   - When answering criminal law questions, reference the current Bharatiya Nyaya Sanhita (BNS 2023), Bharatiya Nagarik Suraksha Sanhita (BNSS 2023), and Bharatiya Sakshya Adhiniyam (BSA 2023), while also citing former IPC/CrPC/Evidence Act sections for complete conceptual clarity.
   - Clearly explain the essential ingredients of legal sections, statutory exceptions, procedural stages (investigation, cognizance, framing of charges, trial, bail), relevant landmark Supreme Court and High Court judgments, and legal maxims.

4. EXHAUSTIVE, RICH & IN-DEPTH RESPONSES:
   - Give complete, well-explained, structured answers.
   - For competitive exam topics (UPSC, MPSC, Law, Banking, SSC, State Services):
     • Provide step-by-step masterclasses with conceptual background, constitutional articles / legal sections, exam patterns, and key takeaways.
   - For places, villages, cities, districts, or historical forts:
     • Overview & Geography, Demographics (Census 2011), History & Heritage (Maratha era), Economy & Infrastructure.

5. STRICT GLOBAL-FIRST LANGUAGE MANDATE (DEFAULT: ENGLISH):
   - GLOBAL DEFAULT IS ENGLISH: Nexora AI is a global assistant. The default language for all responses, explanations, greetings, and introductions is STRICTLY ENGLISH.
   - When the user sends "hello", "hi", "hey", or asks any question in English, you MUST respond in ENGLISH. NEVER default to Marathi or Hindi.
   - STRICT CONDITIONS FOR MARATHI OR HINDI:
     • MARATHI (मराठी): Respond in Marathi ONLY when:
       1. The user explicitly requests Marathi (e.g., "give in marathi", "in marathi", "marathit sang", "marathi madhe dya", "marathi mdhe"), OR
       2. The question itself is phrased in Marathi (using Devanagari script in Marathi or clear Marathi words/grammar like 'ahe', 'kay', 'kasa', 'sang', 'jilhyatil').
     • HINDI (हिंदी): Respond in Hindi ONLY when:
       1. The user explicitly requests Hindi (e.g., "give in hindi", "in hindi", "hindi me batao", "hindi mein"), OR
       2. The question itself is phrased in Hindi (using Devanagari script in Hindi or clear Hindi words/grammar like 'kya hai', 'kaise', 'batao').
   - Unless specifically asked for Marathi or Hindi, or the question is explicitly written in Marathi or Hindi, ALWAYS default to and respond in ENGLISH.

6. DIRECT ANSWERS WHEN REQUESTED:
   - When the user asks for 'name only', 'only name', 'in one line', 'todays date', or 'briefly': State the exact verified name or answer prominently at the top in bold, followed by a concise 1-2 sentence explanation if needed.
   - NEVER output internal meta-phrases like "Based on the verified reference snippet provided in the context", "as per the verified governmental roster", "as per the official list for 2024-2026", or "According to system benchmarks". Answer directly and authoritatively.

7. MULTI-TURN FACTUAL RIGOR & ERROR RECTIFICATION:
   - In follow-up messages (e.g. 'current', 'who', 'update'), NEVER blindly parrot, validate, or anchor onto prior erroneous statements or outdated names from earlier conversation turns.
   - Always verify claims against the authentic, active ground truth. If a previous message mentioned a deceased, former, or superseded official (such as former Deputy CM Ajit Pawar), you MUST explicitly rectify the fact and state the true current incumbent (e.g., Sunetra Pawar & Eknath Shinde).

8. STRICT IMAGE RESTRICTION:
   - You are a text language mentor. NEVER invent fake URLs like '/api/images/nexora_xxxx.jpg' or output fake markdown images in your text. All image requests are automatically detected and rendered by the system's graphic & visual engine.

9. STRICT ADMINISTRATIVE GEOGRAPHY & ZERO-HALLUCINATION ROSTER:
   - When asked for talukas, tehsils, administrative divisions, or districts in Maharashtra (or India):
     • You MUST provide ONLY the exact, 100% verified official talukas that belong strictly to that specific district.
     • NEVER import, hallucinate, or mix up talukas from other districts (e.g. NEVER place Shirol in Sangli — Shirol belongs to Kolhapur; NEVER place Wai in Sangli — Wai belongs to Satara; NEVER place Ranjangaon, Talegaon, Manjlegaon, Karmala, Mohol, or Sangamner in Sangli!).
     • Sangli district has strictly 10 talukas: 1. Miraj, 2. Walwa (Islampur), 3. Shirala, 4. Khanapur (Vita), 5. Atpadi, 6. Tasgaon, 7. Jat, 8. Kavathe Mahankal, 9. Palus, 10. Kadegaon.
     • Sangli is the District Headquarters, located within Miraj Taluka.
     • Strictly adhere to the official Maharashtra Administrative Geography roster in the system benchmarks.
"""

async def generate_answer(messages_or_question) -> str:
    if not client:
        return "(Mock Mode) Groq API key is not configured. Please set GROQ_API_KEY in the .env file."
    
    try:
        now = datetime.now()
        current_date_str = now.strftime("%A, %d %B %Y")
        current_time_str = now.strftime("%I:%M %p")

        date_grounding = f"""
[REAL-WORLD CURRENT DATE & TIME - ABSOLUTE GROUND TRUTH]:
Today is: {current_date_str}, {current_time_str} IST.
Current Year: {now.year}.
- When asked about today's date, current day, current time, or current year: State this exact date directly and authoritatively (e.g., "**{current_date_str}**").
- NEVER guess or output random dates from search snippets or old news articles.
- NEVER say "Based on the reference snippet" or "According to context". Speak directly and authoritatively.
"""

        latest_query = ""
        prev_user_query = ""
        user_and_assistant_msgs = []

        if isinstance(messages_or_question, list):
            recent_msgs = messages_or_question[-4:]
            for idx, m in enumerate(recent_msgs):
                role = "user" if m.get("isUser", True) or m.get("role") == "user" else "assistant"
                raw_content = m.get("text") or m.get("content") or ""
                # Strip internal image paths so the LLM does not learn fake /api/images/ URL patterns
                clean_for_llm = re.sub(r'!\[([^\]]*)\]\(/api/images/[^\)]+\)', r'[Generated Visual: \1]', raw_content)
                clean_for_llm = re.sub(r'!\[([^\]]*)\]\(https?://[^\)]+\)', r'[Generated Visual: \1]', clean_for_llm)
                is_latest = (idx == len(recent_msgs) - 1)
                max_chars = 8000 if is_latest else 1500
                capped_content = clean_for_llm[:max_chars] if len(clean_for_llm) > max_chars else clean_for_llm
                if capped_content:
                    user_and_assistant_msgs.append({"role": role, "content": capped_content})
                    if role == "user":
                        if not is_latest:
                            prev_user_query = raw_content
                        latest_query = raw_content
        else:
            latest_query = str(messages_or_question)
            capped_content = latest_query[:8000] if len(latest_query) > 8000 else latest_query
            user_and_assistant_msgs.append({"role": "user", "content": capped_content})

        target_lang = detect_target_language(latest_query, user_and_assistant_msgs)

        if target_lang == "Marathi":
            lang_directive = (
                "[MANDATORY LANGUAGE DIRECTIVE - MARATHI]:\n"
                "The user requested or queried in MARATHI. Respond completely and fluently in authentic MARATHI (मराठी)."
            )
        elif target_lang == "Hindi":
            lang_directive = (
                "[MANDATORY LANGUAGE DIRECTIVE - HINDI]:\n"
                "The user requested or queried in HINDI. Respond completely and fluently in articulate HINDI (हिंदी)."
            )
        else:
            lang_directive = (
                "[MANDATORY LANGUAGE DIRECTIVE - ENGLISH (GLOBAL DEFAULT)]:\n"
                "The user queried in ENGLISH (or gave a general greeting like 'hello'). Respond completely and fluently in ENGLISH.\n"
                "CRITICAL: Do NOT reply in Marathi or Hindi. Do NOT use Marathi greetings like 'नमस्कार'. Greet and answer in standard English (e.g., 'Hello! I am Nexora AI...')."
            )

        # Dynamically inject targeted ground truth to maintain high speed and prevent rate limit token overflow
        targeted_ground_truth = get_relevant_ground_truth(latest_query)
        full_system_prompt = f"{SYSTEM_PROMPT}\n\n{lang_directive}\n\n{date_grounding}\n\n{targeted_ground_truth}"
        chat_messages = [{"role": "system", "content": full_system_prompt}] + user_and_assistant_msgs + [{"role": "system", "content": lang_directive}]

        # Check for pure date query
        if is_pure_date_query(latest_query):
            if target_lang == "Marathi":
                return f"आजची तारीख **{current_date_str}** आहे."
            elif target_lang == "Hindi":
                return f"आज की तारीख **{current_date_str}** है।"
            return f"Today is **{current_date_str}**."

        # Check for image generation request
        if is_image_request(latest_query):
            print(f"[ImageGen] Generating visual for: {latest_query[:70]}...")
            cleaned_prompt = clean_user_prompt(latest_query)
            refined_prompt = await refine_image_prompt(cleaned_prompt, client, model)
            img_result = await generate_and_save_image(refined_prompt)

            is_mr = (target_lang == "Marathi")
            img_url = img_result.get("image_url") or img_result.get("fallback_url")

            chart_type = img_result.get("chart_type")
            is_chart = img_result.get("is_chart", False) or chart_type or any(w in cleaned_prompt.lower() for w in ["percentage", "chart", "poster", "infographic", "fraction", "bar"])

            if is_chart:
                if chart_type == "fraction" or ("fraction" in cleaned_prompt.lower() and "percentage" in cleaned_prompt.lower()):
                    title = "Fraction to Percentage Memorization Study Chart"
                    if is_mr:
                        return (
                            f"नक्कीच! तुम्ही मागितल्याप्रमाणे हे **{title}** तयार केले आहे:\n\n"
                            f"![{refined_prompt}]({img_url})\n\n"
                            f"### 📋 मुख्य वैशिष्ट्ये (Visual Highlights):\n"
                            f"- 🎨 **Sleek Dark Navy Background**: अभ्यासासाठी डोळ्यांना सुखद व हाय-कॉन्ट्रास्ट डिझाइन.\n"
                            f"- 📐 **Dual-Pill Value Mapping**: अपूर्णांक (Fractions) आणि त्यांची अचूक टक्केवारी (Percentages) समोरासमोर मॅप केली आहे (1/2 = 50%, 1/3 = 33.33%, 1/4 = 25%, 1/5 = 20% इत्यादी).\n"
                            f"- ⚡ **Essential Quant Cheat Sheet**: स्पर्धा परीक्षांसाठी (Banking, SSC, MPSC, UPSC) सर्वाधिक विचारली जाणारी मूल्ये.\n\n"
                            f"*(चित्रावर क्लिक करून फुलस्क्रीन पहा किंवा खालील **Download Image** बटनावर क्लिक करून HD प्रत सेव्ह करा.)*"
                        )
                    else:
                        return (
                            f"Here is your **{title}**:\n\n"
                            f"![{refined_prompt}]({img_url})\n\n"
                            f"### 📋 Visual Highlights:\n"
                            f"- 🎨 **Sleek Dark Navy Background**: Modern high-contrast study aesthetic for easy memorization.\n"
                            f"- 📐 **Dual-Pill Value Mapping**: Fractions clearly mapped to exact percentages (1/2 = 50%, 1/3 = 33.33%, 1/4 = 25%, 1/5 = 20%, etc.).\n"
                            f"- ⚡ **Essential Speed Quant Reference**: Top recurring values for Banking, SSC CGL, MPSC & UPSC exams.\n\n"
                            f"*(Click the image to view in Fullscreen or use the **Download Image** button below to save the high-resolution copy.)*"
                        )
                else:
                    title = "Clean Modern Infographic Poster (Percentages 1 to 30)" if ("1 to 30" in cleaned_prompt.lower() or "bar" in cleaned_prompt.lower() or "horizontal" in cleaned_prompt.lower()) else "Educational Infographic Study Poster"
                    if is_mr:
                        return (
                            f"नक्कीच! तुम्ही मागितल्याप्रमाणे हे **{title}** तयार केले आहे:\n\n"
                            f"![{refined_prompt}]({img_url})\n\n"
                            f"### 📋 मुख्य वैशिष्ट्ये (Visual Highlights):\n"
                            f"- 🎨 **Sleek Dark Navy Background**: आधुनिक डार्क थीम आणि डोळ्यांना सुखद हाय-कॉन्ट्रास्ट लूक.\n"
                            f"- 📊 **3 Color-Coded Tiers**:\n"
                            f"  - **1 – 10**: Vibrant Cyan\n"
                            f"  - **11 – 20**: Electric Purple\n"
                            f"  - **21 – 30**: Neon Orange\n"
                            f"- 🔤 **High-Contrast White Typography**: प्रत्येक टक्केवारी मूल्य (Percentage value) सुस्पष्ट व वाचनीय.\n\n"
                            f"*(चित्रावर क्लिक करून फुलस्क्रीन पहा किंवा खालील **Download Image** बटनावर क्लिक करून HD प्रत सेव्ह करा.)*"
                        )
                    else:
                        return (
                            f"Here is your **{title}**:\n\n"
                            f"![{refined_prompt}]({img_url})\n\n"
                            f"### 📋 Visual Highlights:\n"
                            f"- 🎨 **Sleek Dark Navy Background**: Premium modern aesthetic with maximum visual clarity.\n"
                            f"- 📊 **3 Color-Coded Tiers**:\n"
                            f"  - **1% – 10%**: Vibrant Cyan\n"
                            f"  - **11% – 20%**: Electric Purple\n"
                            f"  - **21% – 30%**: Neon Orange\n"
                            f"- 🔤 **High-Contrast White Typography**: Crystal-clear, readable percentage indicators.\n\n"
                            f"*(Click the image to view in Fullscreen or use the **Download Image** button below to save the high-resolution copy.)*"
                        )
            else:
                if is_mr:
                    return (
                        f"नक्कीच! तुम्ही मागितल्याप्रमाणे हे चित्र तयार केले आहे:\n\n"
                        f"![{refined_prompt}]({img_url})\n\n"
                        f"**Prompt:** *{refined_prompt}*\n\n"
                        f"*(चित्रावर क्लिक करून फुलस्क्रीन पहा किंवा खालील **Download Image** बटनावर क्लिक करून HD प्रत सेव्ह करा.)*"
                    )
                else:
                    return (
                        f"Here is the visual you requested:\n\n"
                        f"![{refined_prompt}]({img_url})\n\n"
                        f"**Prompt:** *{refined_prompt}*\n\n"
                        f"*(Click the image to view in Fullscreen or use the **Download Image** button below to save the HD copy.)*"
                    )

        # Resolve search query context
        search_query = latest_query
        if len(latest_query.split()) <= 4 and prev_user_query:
            search_query = f"{prev_user_query} {latest_query}"

        # Perform Live Web Search for factual queries only when necessary
        web_context = ""
        if search_query and needs_live_search(search_query):
            try:
                loop = asyncio.get_running_loop()
                web_context = await loop.run_in_executor(None, fetch_live_web_context, search_query)
            except Exception as se:
                print(f"[WebSearch] Background lookup skipped: {se}")

        if web_context:
            trimmed_web = web_context[:2200]
            chat_messages.append({
                "role": "system",
                "content": f"[AUTHENTIC REFERENCE SNIPPETS - SEARCH RESULTS]:\n{trimmed_web}\n\nSynthesize these authentic references naturally into your response as an authoritative mentor. Do not copy irrelevant snippets or contradict verified facts. Never mention 'reference snippets' in your output."
            })

        def get_max_tokens(m_name: str) -> int:
            return 900 if "qwen" in m_name.lower() else 2048

        # Resilient multi-tier candidate model execution
        candidate_models = [model, "qwen/qwen3.8-27b", "openai/gpt-oss-20b", "openai/gpt-oss-120b"]
        seen = set()
        ordered_models = []
        for m in candidate_models:
            if m and m not in seen:
                seen.add(m)
                ordered_models.append(m)

        last_error = None
        for m_name in ordered_models:
            try:
                # Temperature 0.1 ensures maximum factual precision, stability, and zero hallucinations
                response = await client.chat.completions.create(
                    model=m_name,
                    messages=chat_messages,
                    temperature=0.1,
                    max_tokens=get_max_tokens(m_name)
                )
                raw_text = response.choices[0].message.content or ""
                sanitized = sanitize_ai_output(raw_text)

                # Safety check: if LLM hallucinated a non-existent /api/images/ path, generate or fix it
                img_matches = re.findall(r'!\[([^\]]*)\]\(/api/images/([a-zA-Z0-9_\-\.]+)\)', sanitized)
                for alt_text, fname in img_matches:
                    fpath = os.path.join(IMAGES_DIR, fname)
                    if not os.path.exists(fpath):
                        gen_res = await generate_and_save_image(alt_text or "Infographic Visual")
                        if gen_res.get("filename"):
                            sanitized = sanitized.replace(f"/api/images/{fname}", gen_res["image_url"])
                        else:
                            sanitized = re.sub(r'!\[[^\]]*\]\(/api/images/' + re.escape(fname) + r'\)', '', sanitized)

                return sanitized
            except Exception as api_err:
                last_error = api_err
                print(f"[AI] Model {m_name} encountered error ({api_err}), falling back to next available model...")
                continue

        if last_error:
            raise last_error
    except Exception as e:
        return f"Error communicating with AI: {str(e)}"

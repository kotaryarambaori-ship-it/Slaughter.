const T={hi:{site:"छोटकू लाल – सफाई कर्मचारी",role:"सरकारी सफाई कर्मचारी",place:"ग्राम पंचायत पांडुव, ब्लॉक बारा, प्रयागराज, उत्तर प्रदेश",
welcome:"गांव को साफ रखना हम सबकी जिम्मेदारी है। कहीं गंदगी दिखे तो यहां शिकायत दर्ज करें।",cta:"शिकायत दर्ज करें",track:"स्थिति देखें",news:"ताज़ा समाचार",nonews:"अभी कोई समाचार नहीं है।",
home:"होम",comp:"शिकायत",trk:"स्थिति",
ctitle:"शिकायत दर्ज करें",name:"आपका नाम",mobile:"मोबाइल नंबर (10 अंक)",cat:"शिकायत का प्रकार",garbage:"कूड़ा / गंदगी",drain:"नाली / जल जमाव",toilet:"शौचालय",road:"सड़क / गली",other:"अन्य",
loc:"गांव / जगह",desc:"समस्या बताएं (कम से कम 10 अक्षर)",send:"शिकायत भेजें",done:"शिकायत दर्ज हो गई। आपका शिकायत नंबर:",keep:"इसे और अपना मोबाइल नंबर संभालकर रखें।",
ttitle:"शिकायत की स्थिति",cno:"शिकायत नंबर",find:"स्थिति खोजें",nf:"शिकायत नहीं मिली। नंबर और मोबाइल जांचें।",
e_name:"नाम कम से कम 2 अक्षर का लिखें।",e_mobile:"सही 10 अंक का मोबाइल नंबर लिखें।",e_category:"शिकायत का प्रकार चुनें।",e_location:"जगह लिखें।",e_description:"समस्या कम से कम 10 अक्षर में लिखें।",e_server:"कुछ गड़बड़ हुई। थोड़ी देर बाद फिर कोशिश करें।",
Pending:"लंबित","In Progress":"काम जारी","Resolved":"हल हो गई","Rejected":"अस्वीकृत",remarks:"टिप्पणी",notice:"यह कोई आधिकारिक सरकारी वेबसाइट नहीं है।"},
en:{site:"Chhotku Lal – Safai Karamchari",role:"Government Safai Karamchari",place:"Gram Panchayat Panduw, Block Bara, Prayagraj, Uttar Pradesh",
welcome:"Keeping our village clean is everyone's job. If you see dirt or waste, file a complaint here.",cta:"File a complaint",track:"Check status",news:"Latest news",nonews:"No news yet.",
home:"Home",comp:"Complaint",trk:"Status",
ctitle:"File a complaint",name:"Your name",mobile:"Mobile number (10 digits)",cat:"Complaint type",garbage:"Garbage / dirt",drain:"Drain / waterlogging",toilet:"Toilet",road:"Road / lane",other:"Other",
loc:"Village / place",desc:"Describe the problem (min 10 characters)",send:"Send complaint",done:"Complaint registered. Your complaint number:",keep:"Keep this and your mobile number safe.",
ttitle:"Complaint status",cno:"Complaint number",find:"Find status",nf:"Complaint not found. Check the number and mobile.",
e_name:"Enter a name of at least 2 letters.",e_mobile:"Enter a valid 10-digit mobile number.",e_category:"Choose a complaint type.",e_location:"Enter the place.",e_description:"Describe the problem in at least 10 characters.",e_server:"Something went wrong. Try again shortly.",
Pending:"Pending","In Progress":"In progress","Resolved":"Resolved","Rejected":"Rejected",remarks:"Remarks",notice:"This is not an official government website."}};
let lang=localStorage.lang||"hi";
const t=k=>T[lang][k]||k;
function apply(){document.documentElement.lang=lang;
 document.querySelectorAll("[data-t]").forEach(e=>e.textContent=t(e.dataset.t));
 document.querySelectorAll("[data-p]").forEach(e=>e.placeholder=t(e.dataset.p));
 document.title=t("site");const b=document.getElementById("lb");if(b)b.textContent=lang=="hi"?"English":"हिन्दी";
 window.onLang&&window.onLang();}
function toggleLang(){lang=lang=="hi"?"en":"hi";localStorage.lang=lang;apply();}
function toggleTheme(){const d=document.documentElement.dataset.theme=="dark"?"light":"dark";document.documentElement.dataset.theme=d;localStorage.theme=d;}
document.documentElement.dataset.theme=localStorage.theme||"light";
addEventListener("DOMContentLoaded",apply);

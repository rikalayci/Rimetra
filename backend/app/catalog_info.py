"""Yerleşik testlerin herkesin anlayabileceği dilde açıklamaları.

Her anahtar için: (bu test nedir, düşük çıkarsa, yüksek/pozitif çıkarsa).
Düşük/yüksek kavramı olmayan testlerde ilgili alan None bırakılır.
Bu metinler genel bilgilendirme içindir; teşhis yerine geçmez.
Uygulama açılışında yalnızca açıklaması hiç girilmemiş (NULL) testlere yazılır,
kullanıcının düzenlediği metinlere dokunulmaz.
"""
from __future__ import annotations

# key: (ne, düşükse, yüksekse)
CATALOG_INFO: dict[str, tuple[str, str | None, str | None]] = {
    # ---------------- Hemogram ----------------
    "blood.wbc": (
        "Kandaki beyaz kan hücrelerinin (akyuvarların) toplam sayısıdır. Bu hücreler vücudun savunma ekibidir; mikroplarla ve iltihapla savaşırlar.",
        "Vücudun savunması zayıflamış olabilir, enfeksiyon kapmak kolaylaşır. Bazı virüs enfeksiyonları, bazı ilaçlar (ör. kemoterapi), B12/folat eksikliği veya kemik iliği sorunları düşürebilir.",
        "Vücut çoğunlukla bir şeyle savaşıyordur: en sık neden enfeksiyondur. Stres, sigara, yoğun egzersiz, kortizon gibi ilaçlar ve gebelik de yükseltebilir. Çok yüksek ve kalıcı değerler doktor tarafından ayrıca incelenir.",
    ),
    "blood.rbc": (
        "Kandaki kırmızı kan hücrelerinin (alyuvarların) sayısıdır. Bu hücreler akciğerden aldıkları oksijeni bütün vücuda taşır.",
        "Kansızlık (anemi) belirtisi olabilir: halsizlik, çabuk yorulma, solukluk, nefes darlığı görülebilir. Demir, B12 veya folat eksikliği, kan kaybı ya da kronik hastalıklar neden olabilir.",
        "Sıvı kaybı (az su içme, ishal) kanı koyulaştırıp değeri yüksek gösterebilir. Sigara, yüksek rakımda yaşama, uzun süreli akciğer hastalıkları da yükseltebilir. Nadiren kemik iliğinin fazla üretim yapmasından olur.",
    ),
    "blood.hgb": (
        "Kırmızı kan hücrelerinin içindeki, oksijeni taşıyan proteindir. Kansızlık olup olmadığını anlamak için en çok bakılan değerdir.",
        "Kansızlık (anemi) anlamına gelir. Yorgunluk, halsizlik, baş dönmesi, solukluk, çarpıntı yapabilir. En sık nedeni demir eksikliğidir; kan kaybı, B12/folat eksikliği ve kalıtsal kan hastalıkları da düşürebilir.",
        "Çoğu zaman vücudun susuz kalmasından kaynaklanır. Sigara içenlerde, yüksek rakımda yaşayanlarda ve bazı akciğer/kalp hastalıklarında da yüksek çıkabilir.",
    ),
    "blood.hct": (
        "Kanın yüzde kaçının kırmızı kan hücrelerinden oluştuğunu gösterir. Kabaca kanın ne kadar 'koyu' olduğunu anlatır; hemoglobinle genelde birlikte iner çıkar.",
        "Kansızlıkta veya kan kaybında düşer. Fazla sıvı alımı da kanı sulandırıp değeri biraz düşük gösterebilir.",
        "Genellikle vücudun susuz kaldığını gösterir. Sigara, yüksek rakım ya da kırmızı hücrelerin fazla üretilmesi de yükseltebilir.",
    ),
    "blood.mcv": (
        "Kırmızı kan hücrelerinin ortalama büyüklüğüdür. Kansızlığın türünü anlamada çok işe yarar.",
        "Hücreler normalden küçüktür. En sık neden demir eksikliğidir; Akdeniz anemisi taşıyıcılığı (talasemi) da hücreleri küçültür.",
        "Hücreler normalden büyüktür. B12 veya folat eksikliği, fazla alkol, karaciğer sorunları, tiroid tembelliği ya da bazı ilaçlar neden olabilir.",
    ),
    "blood.mch": (
        "Bir kırmızı kan hücresinin içinde ortalama ne kadar hemoglobin (oksijen taşıyan protein) olduğunu gösterir.",
        "Hücreler hemoglobin açısından fakirdir; genellikle demir eksikliği veya talasemi taşıyıcılığıyla birlikte görülür.",
        "Genellikle hücreler büyük olduğunda (B12/folat eksikliği gibi) yükselir.",
    ),
    "blood.mchc": (
        "Kırmızı kan hücrelerinin içindeki hemoglobinin ne kadar 'yoğun' olduğunu gösterir; hücrelerin renk koyuluğu gibi düşünülebilir.",
        "Hücreler soluk renklidir; çoğunlukla demir eksikliği kansızlığında görülür.",
        "Seyrek görülür. Bazı kalıtsal kırmızı hücre şekil bozukluklarında ya da numunenin bozulmasıyla (ör. pıhtılaşma, yağlı kan) yanlış yüksek çıkabilir.",
    ),
    "blood.rdw": (
        "Kırmızı kan hücrelerinin boyutlarının birbirinden ne kadar farklı olduğunu (yüzde olarak) gösterir. Hücreler hep aynı boyda ise düşük, karışık boylarda ise yüksek olur.",
        "Düşük olması genellikle bir sorun göstermez.",
        "Kanda hem küçük hem büyük hücreler bir arada var demektir. Demir, B12 veya folat eksikliğinin başlangıcında ya da tedaviye yanıt sırasında sık görülür.",
    ),
    "blood.rdw_sd": (
        "Kırmızı kan hücrelerinin boyut farklılığının bir başka ölçüsüdür (yüzde yerine hacim birimiyle verilir). RDW ile aynı şeyi anlatır.",
        "Düşük olması genellikle bir sorun göstermez.",
        "Hücre boyları arasında farklılık artmıştır; demir, B12 veya folat eksikliğinde sık görülür.",
    ),
    "blood.plt": (
        "Trombositler (kan pulcukları), bir yer kesildiğinde kanamayı durdurmak için tıkaç oluşturan küçük hücrelerdir.",
        "Kolay morarma, diş eti veya burun kanaması, uzun süren kanama olabilir. Virüs enfeksiyonları, bazı ilaçlar, bağışıklık sorunları, karaciğer hastalığı veya B12/folat eksikliği düşürebilir. Bazen tüpte kümelenme nedeniyle yanlış düşük çıkar; tekrar bakılabilir.",
        "Çoğu zaman geçici bir tepkidir: enfeksiyon, iltihap, demir eksikliği veya kan kaybı sonrası yükselebilir. Çok yüksek ve kalıcıysa pıhtı riskini artırabileceği için doktor tarafından değerlendirilir.",
    ),
    "blood.mpv": (
        "Trombositlerin (kan pulcuklarının) ortalama büyüklüğüdür. Genç trombositler daha iri olur.",
        "Trombositler küçüktür; kemik iliğinin üretiminin azaldığı durumlarla ilişkili olabilir. Tek başına çok anlam taşımaz.",
        "Trombositler iridir; kemik iliği hızlı yeni trombosit üretiyor olabilir (ör. trombositlerin hızla tüketildiği durumlarda). Tek başına çok anlam taşımaz.",
    ),
    "blood.pct": (
        "Kanın yüzde kaçının trombositlerden oluştuğunu gösterir. Trombosit sayısı ve büyüklüğünün birleşik bir ölçüsüdür.",
        "Genellikle trombosit sayısı düşük olduğunda düşer.",
        "Genellikle trombosit sayısı yüksek olduğunda yükselir.",
    ),
    "blood.pdw": (
        "Trombositlerin boyutlarının birbirinden ne kadar farklı olduğunu gösterir.",
        "Genellikle bir sorun göstermez.",
        "Trombosit boyları çok çeşitlidir; kemik iliğinin hızlı trombosit ürettiği durumlarda görülebilir. Tek başına çok anlam taşımaz.",
    ),
    "blood.neu_abs": (
        "Nötrofiller, beyaz kan hücrelerinin en kalabalık grubudur ve özellikle bakterilere karşı ilk savunma hattıdır. Bu değer kanda kaç tane olduğunu gösterir.",
        "Bakteri enfeksiyonlarına karşı direnç azalır. Virüs enfeksiyonları, bazı ilaçlar, B12/folat eksikliği düşürebilir. Bazı insanlarda (özellikle bazı etnik kökenlerde) doğuştan biraz düşük ve zararsızdır.",
        "Çoğunlukla bakteri enfeksiyonu, iltihap, stres, sigara, yoğun egzersiz veya kortizon gibi ilaçlarla yükselir.",
    ),
    "blood.lym_abs": (
        "Lenfositler, bağışıklık sisteminin 'hafızası' olan beyaz kan hücreleridir; özellikle virüslerle savaşır ve aşıya yanıt verir. Bu değer kanda kaç tane olduğunu gösterir.",
        "Stres, kortizon kullanımı, bazı virüs enfeksiyonları veya bağışıklığı baskılayan durumlar düşürebilir.",
        "Çoğunlukla virüs enfeksiyonlarında (grip, mononükleoz gibi) geçici olarak yükselir. Uzun süre çok yüksek kalırsa doktor ayrıca inceler.",
    ),
    "blood.mono_abs": (
        "Monositler, vücuttaki mikropları ve hücre artıklarını 'yutarak' temizleyen beyaz kan hücreleridir. Bu değer kanda kaç tane olduğunu gösterir.",
        "Düşük olması genellikle tek başına bir anlam taşımaz; kortizon kullanımında görülebilir.",
        "Uzun süren enfeksiyonlarda, iyileşme döneminde veya kronik iltihaplı hastalıklarda yükselebilir.",
    ),
    "blood.eos_abs": (
        "Eozinofiller, özellikle alerjik reaksiyonlarda ve parazitlere karşı görev alan beyaz kan hücreleridir. Bu değer kanda kaç tane olduğunu gösterir.",
        "Düşük olması genellikle önemli değildir; stres ve kortizon kullanımı düşürür.",
        "En sık nedenleri alerjiler (saman nezlesi, astım, egzama), ilaç alerjisi ve bağırsak parazitleridir.",
    ),
    "blood.baso_abs": (
        "Bazofiller, alerjik tepkilerde rol oynayan, kanda en az bulunan beyaz kan hücreleridir. Bu değer kanda kaç tane olduğunu gösterir.",
        "Normalde zaten çok az olduğu için düşük olması genellikle anlam taşımaz.",
        "Alerjik durumlarda, tiroid tembelliğinde veya bazı kronik iltihaplarda yükselebilir. Belirgin ve kalıcı yükseklik doktor tarafından incelenir.",
    ),
    "blood.neu_pct": (
        "Toplam beyaz kan hücrelerinin yüzde kaçının nötrofil (bakterilere karşı ilk savunma hücresi) olduğunu gösterir. Yorum için yüzdeden çok '# Nötrofil' sayısı önemlidir.",
        "Diğer beyaz hücreler (ör. lenfositler) arttığı için oranı düşmüş olabilir; virüs enfeksiyonlarında sık görülür.",
        "Genellikle bakteri enfeksiyonu, iltihap veya stres durumunda oran artar.",
    ),
    "blood.lym_pct": (
        "Toplam beyaz kan hücrelerinin yüzde kaçının lenfosit (virüslerle savaşan, bağışıklık hafızası olan hücre) olduğunu gösterir. Yorum için '# Lenfosit' sayısı daha önemlidir.",
        "Nötrofiller arttığında (ör. bakteri enfeksiyonu, stres) lenfosit oranı göreceli olarak düşer.",
        "Genellikle virüs enfeksiyonlarında oran artar.",
    ),
    "blood.mono_pct": (
        "Toplam beyaz kan hücrelerinin yüzde kaçının monosit (temizlikçi hücre) olduğunu gösterir.",
        "Genellikle tek başına anlam taşımaz.",
        "Uzun süren enfeksiyonlarda, iyileşme döneminde veya kronik iltihaplarda artabilir.",
    ),
    "blood.eos_pct": (
        "Toplam beyaz kan hücrelerinin yüzde kaçının eozinofil (alerji ve parazitle ilgili hücre) olduğunu gösterir.",
        "Genellikle önemli değildir.",
        "Alerji, astım, egzama, ilaç reaksiyonu veya parazit enfeksiyonu düşündürebilir.",
    ),
    "blood.baso_pct": (
        "Toplam beyaz kan hücrelerinin yüzde kaçının bazofil olduğunu gösterir. Normalde çok küçük bir orandır.",
        "Genellikle anlam taşımaz.",
        "Alerjik durumlarda veya bazı kronik hastalıklarda artabilir; belirgin ve kalıcıysa doktor inceler.",
    ),
    "blood.mentzer": (
        "Laboratuvarın MCV'yi kırmızı kan hücresi sayısına (RBC) bölerek hesapladığı bir sayıdır. Hücreleri küçük çıkan (düşük MCV) kişilerde nedenin demir eksikliği mi yoksa Akdeniz anemisi taşıyıcılığı mı olduğuna dair ilk ipucunu verir. Kesin tanı koydurmaz.",
        "Genellikle 13'ün altı, Akdeniz anemisi (talasemi) taşıyıcılığını düşündürür; doktor gerekirse hemoglobin elektroforezi ister.",
        "Genellikle 13'ün üstü, hücrelerin küçüklüğünün demir eksikliğinden kaynaklandığını düşündürür.",
    ),
    "blood.esr": (
        "Kırmızı kan hücrelerinin bir tüpte bir saatte ne kadar dibe çöktüğünü ölçer. Vücutta genel bir iltihap ya da enfeksiyon olup olmadığına dair kaba bir göstergedir; nerede olduğunu söylemez.",
        "Düşük olması genellikle bir sorun göstermez.",
        "Enfeksiyon, iltihaplı hastalıklar (ör. romatizmal hastalıklar), kansızlık veya böbrek hastalığında yükselebilir. Yaşla, kadınlarda ve gebelikte doğal olarak biraz daha yüksektir.",
    ),
    # ---------------- Biyokimya ----------------
    "serum.glucose": (
        "Kandaki şeker miktarıdır. En az 8 saat aç kalındıktan sonra ölçülür. Vücudun şekeri ne kadar iyi düzenlediğini gösterir.",
        "Titreme, terleme, çarpıntı, baş dönmesi, ani acıkma, dalgınlık yapabilir. Uzun açlık, ağır egzersiz veya şeker ilacı/insülin kullanımında görülebilir.",
        "Açlıkta 100–125 arası 'gizli şeker' (prediyabet), tekrar eden ölçümlerde 126 ve üstü şeker hastalığını düşündürür. Ölçüm öncesi tam aç kalınmadıysa yanlış yüksek çıkabilir. Stres ve kortizon da yükseltir.",
    ),
    "serum.urea": (
        "Proteinler vücutta yıkıldığında oluşan, böbreklerle atılan bir atık maddedir. Böbreklerin çalışmasına dair fikir verir.",
        "Az proteinli beslenme, fazla sıvı alımı, gebelik veya ileri karaciğer hastalığında düşebilir. Genelde önemli değildir.",
        "Az su içme (susuzluk), çok proteinli beslenme, mide-bağırsak kanaması veya böbreklerin yeterince süzememesi durumunda yükselir. Kreatininle birlikte yorumlanır.",
    ),
    "serum.bun": (
        "Kan üre azotu; üre ile aynı şeyi ölçer, sadece farklı bir hesaplamayla verilir (yaklaşık olarak Üre ÷ 2,14). Böbrek çalışmasına dair fikir verir.",
        "Az proteinli beslenme, fazla sıvı alımı veya karaciğer hastalığında düşebilir. Genelde önemli değildir.",
        "Susuzluk, yüksek protein alımı, mide-bağırsak kanaması veya böbrek çalışmasının azalmasıyla yükselir.",
    ),
    "serum.creatinine": (
        "Kaslarda sürekli üretilen ve böbreklerle atılan bir atık maddedir. Böbreklerin süzme gücünü gösteren en önemli değerlerden biridir.",
        "Kas kütlesi az olanlarda (zayıf, yaşlı kişiler), gebelikte görülür. Genelde önemli değildir.",
        "Böbreklerin süzme gücü azalmış olabilir. Susuzluk, çok yoğun egzersiz, kas kütlesinin fazla olması, çok et yeme ve bazı ilaçlar da geçici olarak yükseltebilir.",
    ),
    "serum.egfr": (
        "Böbreklerin dakikada ne kadar kan süzebildiğinin tahminidir. Kreatinin, yaş ve cinsiyetten hesaplanır. 90 ve üstü normal kabul edilir; yaşla birlikte biraz azalması doğaldır.",
        "Böbreklerin süzme gücü azalmıştır. 60'ın altında ve en az 3 ay böyle kalırsa kronik böbrek hastalığı açısından değerlendirilir. Susuzluk ve bazı ilaçlar geçici olarak düşürebilir.",
        "Yüksek olması genellikle sorun değildir.",
    ),
    "serum.uric_acid": (
        "Vücutta bazı besinlerin (özellikle kırmızı et, sakatat, bazı deniz ürünleri) ve hücrelerin yıkımıyla oluşan, böbrekle atılan bir atıktır.",
        "Düşük olması genellikle önemli değildir.",
        "Eklemlerde birikip gut hastalığına (ani, çok ağrılı eklem şişliği, sıklıkla ayak başparmağında) veya böbrek taşına yol açabilir. Kırmızı et, sakatat, alkol (özellikle bira), şekerli içecekler, fazla kilo ve bazı ilaçlar yükseltir.",
    ),
    "serum.alt": (
        "Çoğunlukla karaciğer hücrelerinde bulunan bir enzimdir. Karaciğer hücreleri zarar gördüğünde kana karışır. Karaciğerin en hassas göstergelerinden biridir.",
        "Düşük olması genellikle önemli değildir.",
        "Karaciğer hücreleri bir şekilde zorlanıyor olabilir: yağlı karaciğer, alkol, bazı ilaçlar ve takviyeler, hepatit (sarılık) virüsleri en sık nedenlerdir. Ağır egzersiz sonrası da hafif yükselebilir.",
    ),
    "serum.ast": (
        "Karaciğerde ama aynı zamanda kaslarda ve kalpte de bulunan bir enzimdir. ALT ile birlikte yorumlanır.",
        "Düşük olması genellikle önemli değildir.",
        "Karaciğer zorlanması (yağlanma, alkol, hepatit, ilaçlar) veya kas hasarı (ağır egzersiz, kas yaralanması) yükseltebilir. ALT ile birlikte bakılınca kaynağı hakkında ipucu verir.",
    ),
    "serum.ggt": (
        "Karaciğer ve safra yollarında bulunan bir enzimdir. Alkole ve bazı ilaçlara karşı çok hassastır.",
        "Düşük olması genellikle önemli değildir.",
        "Alkol kullanımı, yağlı karaciğer, safra yollarında tıkanma, bazı ilaçlar (ör. sara ilaçları) yükseltebilir.",
    ),
    "serum.alp": (
        "Başlıca karaciğer, safra yolları ve kemiklerde bulunan bir enzimdir. Çocuklarda ve gençlerde kemikler büyüdüğü için doğal olarak yüksektir; gebelikte de artar.",
        "Seyrek görülür; çinko veya magnezyum eksikliği, beslenme bozukluğu ya da tiroid tembelliğinde düşebilir.",
        "Safra yollarında tıkanma (taş vb.), karaciğer sorunları veya kemik hastalıkları (D vitamini eksikliği, kırık iyileşmesi gibi) yükseltebilir. GGT de yüksekse kaynak büyük ihtimalle karaciğer/safra yoludur.",
    ),
    "serum.ldh": (
        "Neredeyse tüm dokularda bulunan bir enzimdir. Herhangi bir yerde hücre hasarı olduğunda kana karışır; nerede olduğunu tek başına söylemez.",
        "Düşük olması genellikle önemli değildir.",
        "Kas yaralanması, ağır egzersiz, kırmızı kan hücrelerinin parçalanması, karaciğer hastalığı veya enfeksiyonlar yükseltebilir. Kan alındıktan sonra tüpte hücreler parçalanırsa da yanlış yüksek çıkabilir.",
    ),
    "serum.bili_total": (
        "Eski kırmızı kan hücreleri yıkıldığında oluşan sarı renkli bir maddedir. Karaciğer bunu işleyip safrayla atar. Yüksek olunca deri ve göz akı sararır (sarılık).",
        "Düşük olması önemli değildir.",
        "Karaciğerin veya safra yollarının çalışmasında sorun ya da kırmızı hücrelerin hızlı yıkılması olabilir. Toplumda sık görülen, zararsız 'Gilbert sendromu'nda açlık ve stresle hafif yükselir.",
    ),
    "serum.bili_direct": (
        "Bilirubinin karaciğerde işlenmiş (safraya atılmaya hazır) kısmıdır. Sarılığın nedenini ayırt etmeye yardım eder.",
        "Düşük olması önemli değildir.",
        "Karaciğer hücrelerinde sorun veya safra yollarında tıkanma (taş, daralma gibi) olabilir.",
    ),
    "serum.total_protein": (
        "Kandaki tüm proteinlerin toplamıdır (çoğu albümin ve antikorlardır). Beslenme durumu, karaciğer ve böbrek sağlığı hakkında genel bilgi verir.",
        "Yetersiz beslenme, karaciğer hastalığı, böbreklerden protein kaçağı veya bağırsaktan emilim sorunlarında düşebilir.",
        "En sık susuzluk nedeniyle yüksek görünür. Uzun süren iltihaplı hastalıklarda veya nadiren bazı kan hastalıklarında da artabilir.",
    ),
    "serum.albumin": (
        "Karaciğerin ürettiği, kandaki en bol proteindir. Kanın damar içinde kalmasını sağlar ve birçok maddeyi taşır. Beslenme ve karaciğer durumunu yansıtır.",
        "Yetersiz beslenme, karaciğer hastalığı, böbreklerden protein kaçağı veya uzun süreli hastalıkta düşer. Çok düşükse ayaklarda şişlik (ödem) olabilir.",
        "Neredeyse her zaman susuzluk (kanın koyulaşması) nedeniyle yüksek görünür.",
    ),
    "serum.sodium": (
        "Kandaki tuzun temel parçasıdır. Vücuttaki su dengesini, sinir ve kas çalışmasını düzenler.",
        "Çoğunlukla vücutta tuza göre fazla su olduğunu gösterir. Çok fazla su içme, bazı idrar söktürücü ve depresyon ilaçları, kusma/ishal, kalp veya böbrek yetmezliği neden olabilir. Belirgin düşüklükte baş ağrısı, bulantı, bilinç bulanıklığı olabilir.",
        "Çoğunlukla vücudun su kaybettiğini gösterir (az su içme, ishal, çok terleme). Susuzluk hissi, ağız kuruluğu, halsizlik görülebilir.",
    ),
    "serum.potassium": (
        "Kalbin ve kasların düzgün çalışması için çok önemli bir mineraldir. Küçük değişiklikler bile kalp ritmini etkileyebilir.",
        "Kusma, ishal, idrar söktürücü ilaçlar düşürebilir. Kas güçsüzlüğü, kramp, kabızlık ve çarpıntı yapabilir.",
        "Böbrek yetmezliği, bazı tansiyon ilaçları veya potasyum takviyesi yükseltebilir. Kalp ritmini bozabileceği için önemlidir. Ancak kan alınırken hücreler parçalanırsa tüpte yanlış yüksek de çıkabilir; doktor tekrar ölçtürebilir.",
    ),
    "serum.chloride": (
        "Sodyumla birlikte vücudun su ve asit-baz dengesini sağlayan bir tuz mineralidir. Genellikle sodyumla birlikte iner çıkar.",
        "Uzun süren kusma, bazı idrar söktürücü ilaçlar veya fazla su alımı düşürebilir.",
        "Susuzluk, ishal veya bazı böbrek sorunları yükseltebilir.",
    ),
    "serum.calcium": (
        "Kemik ve dişlerin temel yapıtaşıdır; ayrıca kasların, sinirlerin ve kalbin çalışması için gereklidir. Kanda albüminle birlikte taşındığı için albümin düşükse kalsiyum da düşük görünebilir.",
        "D vitamini eksikliği, albümin düşüklüğü, böbrek hastalığı veya paratiroid bezinin az çalışmasıyla düşer. Ellerde/dudak çevresinde karıncalanma, kas krampları yapabilir.",
        "En sık nedeni boyundaki paratiroid bezlerinin fazla çalışmasıdır. Fazla kalsiyum veya D vitamini takviyesi, bazı ilaçlar da yükseltebilir. Susuzluk, kabızlık, böbrek taşı, halsizlik yapabilir.",
    ),
    "serum.phosphorus": (
        "Kalsiyumla birlikte kemiklerin yapısında yer alan ve hücrelerin enerji üretimi için gereken bir mineraldir.",
        "Yetersiz beslenme, alkol, D vitamini eksikliği, bazı mide ilaçları veya paratiroid bezinin fazla çalışmasıyla düşebilir.",
        "En sık nedeni böbreklerin yeterince atamamasıdır. Çocuklarda büyüme nedeniyle doğal olarak yüksektir. Kan tüpte bekleyip hücreler parçalanırsa yanlış yüksek de çıkabilir.",
    ),
    "serum.magnesium": (
        "Kasların, sinirlerin ve kalbin düzgün çalışması, enerji üretimi için gereken bir mineraldir.",
        "Yetersiz beslenme, alkol, ishal, bazı mide koruyucu (asit baskılayıcı) ve idrar söktürücü ilaçlar düşürebilir. Kas krampları, seğirme, halsizlik, çarpıntı yapabilir.",
        "Genellikle böbrek yetmezliğinde veya magnezyum içeren ilaç/takviyelerin fazla alınmasında görülür.",
    ),
    "serum.ck": (
        "Kaslarda (iskelet kası ve kalp) bol bulunan bir enzimdir. Kas zorlandığında veya hasar gördüğünde kana karışır.",
        "Kas kütlesi az olanlarda düşük olabilir; genelde önemli değildir.",
        "En sık neden yoğun egzersiz, kas zorlanması, düşme, iğne yapılması gibi kas hasarlarıdır. Kolesterol ilaçları (statinler) kas ağrısıyla birlikte yükseltebilir. Çok yüksek değerler böbreğe zarar verebileceği için önemlidir.",
    ),
    "serum.amylase": (
        "Nişastayı sindiren bir enzimdir; başlıca pankreastan ve tükürük bezlerinden salgılanır.",
        "Düşük olması genellikle önemli değildir.",
        "Pankreas iltihabı (şiddetli karın üst kısmı ağrısı ile), tükürük bezi iltihabı (kabakulak gibi) veya böbrek yetmezliğinde yükselebilir.",
    ),
    "serum.lipase": (
        "Yağları sindiren, pankreastan salgılanan bir enzimdir. Pankreas için amilazdan daha özgül bir göstergedir.",
        "Düşük olması genellikle önemli değildir.",
        "Belirgin yükseklik (normalin birkaç katı) pankreas iltihabını düşündürür. Hafif yükseklik böbrek yetmezliği veya başka karın içi sorunlarda da görülebilir.",
    ),
    # ---------------- Lipid ----------------
    "serum.chol_total": (
        "Kandaki toplam kolesterol miktarıdır. Kolesterol vücut için gerekli bir yağdır ama fazlası damar duvarında birikir. 'İyi' (HDL) ve 'kötü' (LDL) kolesterolün toplamı gibi düşünülebilir.",
        "Genellikle bir sorun göstermez. Çok düşükse yetersiz beslenme, tiroidin fazla çalışması veya karaciğer hastalığı akla gelebilir.",
        "Damar sertliği, kalp krizi ve inme riskini artırabilir. Ancak toplam değer tek başına yeterli değildir; LDL ve HDL'ye birlikte bakılır. Kalıtım, beslenme, hareketsizlik ve tiroid tembelliği yükseltir.",
    ),
    "serum.hdl": (
        "'İyi kolesterol' olarak bilinir. Damarlardaki fazla kolesterolü toplayıp karaciğere geri taşır, yani damarları korur. Yüksek olması iyidir.",
        "Kalp-damar hastalığı riski artar. Sigara, hareketsizlik, fazla kilo, şeker hastalığı ve trigliserid yüksekliği düşürür. Düzenli egzersiz ve sigarayı bırakmak yükseltir.",
        "Genellikle olumlu kabul edilir.",
    ),
    "serum.ldl": (
        "'Kötü kolesterol' olarak bilinir. Damar duvarında birikip plak oluşturarak damar sertliğine yol açar. Kalp-damar riskinin en önemli göstergesidir; ideal hedef kişinin risk durumuna göre değişir.",
        "Genellikle olumlu kabul edilir.",
        "Kalp krizi ve inme riskini artırır. Doymuş yağlarca zengin beslenme, hareketsizlik, kalıtım ve tiroid tembelliği yükseltir. Hedef değer yaşa, şeker hastalığı, tansiyon ve sigara durumuna göre doktor tarafından belirlenir.",
    ),
    "serum.vldl": (
        "Kanda trigliseridleri (yağları) taşıyan bir kolesterol türüdür. Çoğunlukla doğrudan ölçülmez, trigliseridden hesaplanır (yaklaşık trigliserid ÷ 5).",
        "Genellikle bir sorun göstermez.",
        "Trigliseridin yüksek olduğunu gösterir; damar sertliği riskine katkıda bulunur.",
    ),
    "serum.triglyceride": (
        "Kandaki ana yağ türüdür. Yediğimiz fazla kalori (özellikle şeker, un ve alkol) vücutta trigliseride çevrilip depolanır. Yemekten sonra yükseldiği için aç karnına ölçülmesi önemlidir.",
        "Genellikle bir sorun göstermez.",
        "Kalp-damar hastalığı riskini artırır. Fazla şeker ve beyaz un, alkol, fazla kilo, hareketsizlik ve kontrolsüz şeker hastalığı yükseltir. Çok yüksek değerler (500 üstü) pankreas iltihabı riski taşır. Ölçüm öncesi aç kalınmadıysa yanlış yüksek çıkabilir.",
    ),
    "serum.non_hdl": (
        "Toplam kolesterolden 'iyi' kolesterol (HDL) çıkarılarak hesaplanır. Damara zarar verebilecek tüm kolesterol türlerinin toplamıdır. Özellikle trigliseridi yüksek olanlarda LDL'den daha iyi bir risk göstergesi olabilir.",
        "Genellikle olumlu kabul edilir.",
        "Kalp-damar hastalığı riski artmıştır; LDL yüksekliğiyle aynı anlama gelir.",
    ),
    # ---------------- Tiroid ----------------
    "serum.tsh": (
        "Beyindeki hipofiz bezinin salgıladığı ve tiroid bezine 'hormon üret' komutu veren hormondur. Tiroidin nasıl çalıştığına dair ilk bakılan testtir. Mantığı tersinedir: tiroid az çalışırsa TSH yükselir, fazla çalışırsa düşer.",
        "Genellikle tiroidin fazla çalıştığını gösterir (hipertiroidi): çarpıntı, kilo kaybı, sıcağa dayanamama, terleme, el titremesi, sinirlilik olabilir. Fazla tiroid ilacı kullanımı da düşürür.",
        "Genellikle tiroidin az çalıştığını gösterir (hipotiroidi, 'tiroid tembelliği'): yorgunluk, kilo alma, üşüme, kabızlık, cilt kuruluğu, saç dökülmesi olabilir. Hafif yükseklikler hastalık veya iyileşme dönemlerinde geçici olabilir.",
    ),
    "serum.ft4": (
        "Tiroid bezinin ürettiği ana hormondur (tiroksin). 'Serbest' olan, kanda vücudun hemen kullanabileceği kısmıdır. TSH ile birlikte yorumlanır.",
        "Tiroidin az çalıştığını gösterebilir (yorgunluk, kilo alma, üşüme). TSH ile birlikte değerlendirilir.",
        "Tiroidin fazla çalıştığını gösterebilir (çarpıntı, kilo kaybı, terleme) ya da fazla tiroid ilacı kullanıldığını. Biotin (B7) takviyesi de bazı cihazlarda sonucu bozabilir.",
    ),
    "serum.ft3": (
        "Tiroid hormonunun en etkili, aktif şeklidir. Çoğunlukla T4'ün vücutta dönüştürülmesiyle oluşur.",
        "Tiroid az çalışıyor olabilir; ancak ağır hastalık, açlık veya diyet dönemlerinde tiroid sağlıklıyken de düşebilir.",
        "Tiroidin fazla çalıştığını gösterebilir.",
    ),
    "serum.anti_tpo": (
        "Vücudun bağışıklık sisteminin yanlışlıkla kendi tiroid bezine karşı ürettiği bir antikordur. Tiroid sorununun bağışıklık kaynaklı olup olmadığını gösterir.",
        "Negatif ya da düşük olması normaldir.",
        "En sık Hashimoto hastalığını gösterir (bağışıklık sisteminin tiroidi yavaş yavaş zayıflatması). Pozitif olması hemen tedavi gerektiği anlamına gelmez, ama ileride tiroid tembelliği gelişme olasılığını artırır; TSH'nin düzenli takibi önerilir. Graves hastalığında da pozitif olabilir.",
    ),
    "serum.anti_tg": (
        "Bağışıklık sisteminin tiroid bezindeki tiroglobulin adlı proteine karşı ürettiği antikordur. Anti-TPO ile birlikte bağışıklık kaynaklı tiroid hastalıklarını araştırmak için bakılır.",
        "Negatif ya da düşük olması normaldir.",
        "Hashimoto veya Graves gibi bağışıklık kaynaklı tiroid hastalıklarını düşündürür. Sağlıklı insanlarda da bazen hafif pozitif çıkabilir.",
    ),
    # ---------------- Vitamin ve mineral ----------------
    "serum.b12": (
        "Sinir sistemi, kan yapımı ve DNA üretimi için gerekli bir vitamindir. Çoğunlukla hayvansal besinlerde (et, yumurta, süt) bulunur.",
        "Yorgunluk, halsizlik, unutkanlık, el-ayakta uyuşma/karıncalanma, kansızlık yapabilir. Vejetaryen/vegan beslenme, mide sorunları, uzun süre mide koruyucu (asit baskılayıcı) veya metformin kullanımı ve ileri yaş riskini artırır.",
        "Genellikle B12 takviyesi veya iğnesi kullanımına bağlıdır ve zararsızdır. Takviye olmadan belirgin yükseklik nadiren karaciğer veya kan hastalıklarıyla ilişkili olabilir.",
    ),
    "serum.vit_d": (
        "Kemik sağlığı için kalsiyumun emilmesini sağlayan vitamindir; bağışıklık ve kas sağlığında da rol oynar. Çoğunlukla güneş ışığıyla deride üretilir.",
        "Çok yaygındır. Yorgunluk, kemik ve kas ağrıları, kas güçsüzlüğü yapabilir; uzun süreli eksiklik kemikleri zayıflatır. Güneşe az çıkmak, kapalı giyinmek, koyu ten ve fazla kilo riski artırır. Genellikle 20'nin altı eksiklik, 20–30 arası yetersizlik kabul edilir.",
        "Neredeyse her zaman fazla D vitamini takviyesi kullanımından olur. Çok yüksek değerler kanda kalsiyumu yükseltip bulantı, susuzluk, böbrek taşı yapabilir.",
    ),
    "serum.folate": (
        "Folik asit olarak da bilinen B vitaminidir. Kan hücrelerinin yapımı ve gebelikte bebeğin sinir sisteminin gelişimi için çok önemlidir. Yeşil yapraklı sebzeler ve baklagillerde bolca bulunur.",
        "Kansızlık, yorgunluk, ağızda yara yapabilir. Yetersiz sebze tüketimi, alkol, bazı ilaçlar ve gebelik eksikliği artırır.",
        "Genellikle takviye kullanımına bağlıdır ve zararsızdır.",
    ),
    "serum.ferritin": (
        "Vücuttaki demir deposunun göstergesidir. Demir eksikliğini anlamak için en güvenilir testtir.",
        "Demir depoları boşalmıştır. Kansızlık henüz başlamamış olsa bile yorgunluk, saç dökülmesi, tırnak kırılması yapabilir. En sık nedenleri kan kaybı (adet kanamaları dahil), yetersiz demir alımı ve emilim sorunlarıdır.",
        "Ferritin, iltihap ve enfeksiyon sırasında da yükselir; bu durumda gerçek demir deposunu yansıtmayabilir. Karaciğer yağlanması, alkol veya vücutta aşırı demir birikmesi (hemokromatozis) de yükseltebilir.",
    ),
    "serum.iron": (
        "Kandaki o anki demir miktarıdır. Demir, hemoglobinin yapımı için gereklidir. Gün içinde ve yemeklere göre çok değiştiği için tek başına güvenilir değildir; ferritin ve demir bağlama kapasitesiyle birlikte yorumlanır.",
        "Demir eksikliği veya uzun süren iltihaplı hastalık olabilir. Akşam saatlerinde doğal olarak daha düşüktür.",
        "Yakın zamanda demir hapı alınması veya demir açısından zengin bir öğün yükseltebilir. Kalıcı yükseklik vücutta demir birikmesini düşündürebilir.",
    ),
    "serum.tibc": (
        "Kanın demir taşıma kapasitesinin toplamıdır. Vücut demire ihtiyaç duyduğunda bu kapasiteyi artırır; yani demir azaldıkça bu değer yükselir.",
        "Vücutta demir fazlalığı, kronik iltihap, yetersiz beslenme veya karaciğer hastalığında düşebilir.",
        "Genellikle demir eksikliğini gösterir: vücut daha fazla demir yakalamaya çalışmaktadır. Gebelik ve doğum kontrol hapları da yükseltebilir.",
    ),
    "serum.uibc": (
        "Kanın demir taşıyıcılarında hâlâ boş olan (demirle dolmamış) kapasitedir. Demir azaldıkça boş yerler artar, bu değer yükselir.",
        "Taşıyıcılar demirle dolu demektir; vücutta demir fazlalığı veya kronik iltihap olabilir.",
        "Genellikle demir eksikliğini gösterir.",
    ),
    "serum.zinc": (
        "Bağışıklık, yara iyileşmesi, tat-koku duyusu, saç ve cilt sağlığı için gereken bir mineraldir.",
        "Sık enfeksiyon, yara iyileşmesinde gecikme, saç dökülmesi, tat-koku azalması yapabilir. Yetersiz beslenme, ishal, alkol ve bazı bağırsak hastalıkları neden olabilir.",
        "Genellikle fazla çinko takviyesi kullanımından olur; uzun süre yüksek kalırsa bakır eksikliğine yol açabilir.",
    ),
    # ---------------- Diyabet ----------------
    "blood.hba1c": (
        "Son 2–3 aylık ortalama kan şekerini gösterir. Açlık şekeri gibi o güne bağlı değildir; şeker hastalığının teşhisi ve takibinde en önemli testlerden biridir.",
        "Genellikle olumlu kabul edilir. Kansızlık, yakın zamanda kan kaybı veya kan nakli değeri yanlış düşük gösterebilir.",
        "%5,7–6,4 arası 'gizli şeker' (prediyabet), %6,5 ve üstü şeker hastalığı anlamına gelir. Şeker hastası olanlarda yüksek değer, şekerin son aylarda iyi kontrol edilmediğini gösterir. Demir eksikliği de değeri biraz yükseltebilir.",
    ),
    "serum.insulin": (
        "Pankreasın salgıladığı ve şekerin kandan hücrelere girmesini sağlayan hormondur. Genellikle açken ölçülür ve açlık şekeriyle birlikte yorumlanır.",
        "Aç karnına düşük olması genellikle normaldir. Şeker de yüksekse pankreasın yeterli insülin üretemediğini düşündürebilir.",
        "Vücudun insüline karşı duyarsızlaştığını (insülin direnci) gösterebilir; pankreas şekeri düşürmek için daha çok çalışmak zorunda kalır. Fazla kilo (özellikle karın bölgesinde), hareketsizlik ve polikistik over sendromuyla sıktır. İleride şeker hastalığı riskini artırır.",
    ),
    # ---------------- İnflamasyon ----------------
    "serum.crp": (
        "Vücutta iltihap veya enfeksiyon olduğunda karaciğerin hızla ürettiği bir proteindir. Sorunun nerede olduğunu söylemez ama 'vücutta bir şeyle savaşılıyor mu' sorusuna hızlı yanıt verir.",
        "Düşük olması normaldir ve vücutta belirgin bir iltihap olmadığını gösterir.",
        "Enfeksiyon (özellikle bakteri), yaralanma, ameliyat sonrası veya iltihaplı hastalıklarda yükselir. Değer yükseldikçe iltihabın şiddeti genelde artar; tedaviyle birlikte düşmesi beklenir.",
    ),
    "serum.hs_crp": (
        "CRP'nin çok hassas yöntemle ölçülmesidir. Belirgin bir hastalık yokken damarlardaki düşük düzeyli iltihabı ölçerek kalp-damar hastalığı riskini değerlendirmek için kullanılır.",
        "1 mg/L'nin altı düşük kalp-damar riski olarak kabul edilir.",
        "1–3 arası orta, 3'ün üstü yüksek kalp-damar riski olarak yorumlanır. Ancak o sırada geçirilen bir enfeksiyon da yükseltir; 10'un üzerinde ise risk değerlendirmesi yerine aktif bir iltihap aranır.",
    ),
    "serum.procalcitonin": (
        "Özellikle bakteri enfeksiyonlarında yükselen bir maddedir. Enfeksiyonun bakteriden mi virüsten mi kaynaklandığını ayırt etmeye ve antibiyotik kararına yardımcı olur.",
        "Düşük olması bakteri enfeksiyonu olasılığını azaltır.",
        "Bakteri enfeksiyonunu düşündürür; çok yüksek değerler ciddi, yayılmış bir enfeksiyonu gösterebilir. Büyük ameliyat veya yaralanma sonrasında da yükselebilir.",
    ),
    # ---------------- Hormon ----------------
    "serum.cortisol": (
        "Böbreküstü bezlerinin salgıladığı 'stres hormonu'dur. Şeker, tansiyon ve bağışıklığın düzenlenmesinde rol alır. Sabah en yüksek, gece en düşüktür; bu yüzden genellikle sabah ölçülür.",
        "Böbreküstü bezlerinin yeterince hormon üretemediğini gösterebilir: halsizlik, kilo kaybı, tansiyon düşüklüğü, tuz isteği olabilir. Uzun süre kortizon ilacı kullanıp aniden bırakmak da düşürür.",
        "Stres, akut hastalık, uykusuzluk ve doğum kontrol hapları yükseltebilir. Kalıcı belirgin yükseklik, böbreküstü bezinin fazla çalışmasıyla ilgili hastalıkları (Cushing) düşündürebilir.",
    ),
    "serum.prolactin": (
        "Beyindeki hipofiz bezinden salgılanan ve doğumdan sonra süt yapımını sağlayan hormondur.",
        "Genellikle önemli değildir.",
        "Kadınlarda adet düzensizliği, gebe değilken memeden süt gelmesi, gebe kalmada zorluk; erkeklerde cinsel istek azalması yapabilir. Stres, uykusuzluk, gebelik, emzirme, bazı ilaçlar (mide ve psikiyatri ilaçları), tiroid tembelliği ve hipofizdeki küçük iyi huylu tümörler yükseltebilir.",
    ),
    "serum.testosterone": (
        "Başlıca erkeklik hormonudur; kadınlarda da az miktarda bulunur. Kas kütlesi, kemik sağlığı, cinsel istek ve enerji düzeyini etkiler. Sabah en yüksektir; genellikle sabah ölçülür.",
        "Erkeklerde cinsel istek azalması, sertleşme sorunları, yorgunluk, kas kaybı, ruh hali değişiklikleri yapabilir. Fazla kilo, şeker hastalığı, ileri yaş, uykusuzluk düşürebilir.",
        "Kadınlarda sivilce, istenmeyen tüylenme, adet düzensizliği yapabilir; en sık nedeni polikistik over sendromudur. Erkeklerde dışarıdan hormon/steroid kullanımı yükseltebilir.",
    ),
    "serum.estradiol": (
        "Başlıca kadınlık hormonudur (östrojen). Adet döngüsü, kemik sağlığı ve üreme için önemlidir. Kadınlarda adet döngüsünün gününe göre çok değişir; erkeklerde de az miktarda bulunur.",
        "Kadınlarda menopoz, yumurtalıkların az çalışması, aşırı zayıflık veya çok yoğun egzersizde görülür. Sıcak basması, adet düzensizliği, kemik zayıflaması yapabilir.",
        "Kadınlarda döngünün belli günlerinde, gebelikte ve hormon tedavisinde normaldir. Erkeklerde fazla kilo nedeniyle yükselebilir; meme büyümesi yapabilir.",
    ),
    "serum.fsh": (
        "Beyindeki hipofiz bezinden salgılanır; kadınlarda yumurtalıkları, erkeklerde sperm üretimini uyarır. Kadınlarda adet döngüsüne göre değişir.",
        "Hipofiz bezinin yeterince uyarı göndermediğini gösterebilir; aşırı zayıflık, yoğun stres veya çok yoğun egzersizde de görülür.",
        "Kadınlarda menopoz döneminde doğal olarak yükselir; daha erken yaşta yüksekse yumurta rezervinin azaldığını düşündürür. Erkeklerde testislerin sperm üretiminde sorun olabileceğini gösterebilir.",
    ),
    "serum.lh": (
        "Beyindeki hipofiz bezinden salgılanır; kadınlarda yumurtlamayı, erkeklerde testosteron üretimini tetikler. Kadınlarda yumurtlamadan hemen önce ani bir yükselme yapar.",
        "Hipofiz bezinin az çalıştığını gösterebilir; aşırı zayıflık ve yoğun stres de düşürebilir.",
        "Kadınlarda yumurtlama zamanında ve menopozda normaldir. Polikistik over sendromunda LH/FSH oranı artabilir. Erkeklerde testislerin az çalıştığını gösterebilir.",
    ),
    "serum.psa_total": (
        "Prostat bezinin ürettiği bir proteindir; erkeklerde prostat sağlığının takibinde kullanılır. Yaşla birlikte doğal olarak biraz artar.",
        "Düşük olması olumludur.",
        "En sık nedeni prostatın iyi huylu büyümesi veya prostat iltihabıdır. Bisiklete binme, cinsel ilişki (son 48 saat), idrar sondası da geçici olarak yükseltebilir. Belirgin yükseklik veya hızlı artış durumunda doktor prostat kanserini dışlamak için ileri tetkik isteyebilir.",
    ),
    "serum.psa_free": (
        "PSA'nın kanda proteinlere bağlı olmayan, serbest dolaşan kısmıdır. Total PSA'yla birlikte oran olarak yorumlanır.",
        "Total PSA'ya göre oranı düşükse ileri inceleme gerekebilir (bkz. Serbest/Total PSA Oranı).",
        "Total PSA'ya göre oranının yüksek olması genellikle iyi huylu prostat büyümesini düşündürür.",
    ),
    "serum.psa_ratio": (
        "Serbest PSA'nın total PSA'ya oranıdır. Özellikle total PSA hafif yüksek (yaklaşık 4–10 ng/mL arası) olduğunda, iyi huylu büyüme ile kanser riskini ayırt etmeye yardım eder.",
        "Oran düşükse (genellikle %10–15'in altı) prostat kanseri olasılığı artar; doktor ileri tetkik isteyebilir.",
        "Oran yüksekse (genellikle %25'in üstü) yükselmenin iyi huylu prostat büyümesine bağlı olma ihtimali daha yüksektir.",
    ),
    # ---------------- Koagülasyon ----------------
    "blood.pt": (
        "Kanın belli bir yoldan pıhtılaşmasının kaç saniye sürdüğünü ölçer. Karaciğer işlevi ve kan sulandırıcı ilaç (varfarin/Coumadin) takibinde kullanılır.",
        "Kısa olması genellikle bir sorun göstermez.",
        "Kanın pıhtılaşması yavaşlamıştır; kanama eğilimi olabilir. Varfarin gibi kan sulandırıcılar, K vitamini eksikliği veya karaciğer hastalığı uzatır.",
    ),
    "blood.inr": (
        "Protrombin zamanının (PT) laboratuvardan bağımsız, standart hale getirilmiş sonucudur. Kan sulandırıcı kullanmayan sağlıklı birinde yaklaşık 1'dir. Varfarin kullananlarda hedef genellikle 2–3 arasıdır.",
        "Varfarin kullananlarda hedefin altında olması kanın yeterince sulanmadığını, pıhtı riskinin sürdüğünü gösterir.",
        "Kan geç pıhtılaşıyordur; kanama riski artar. Varfarin dozunun fazla gelmesi, bazı ilaç/antibiyotik etkileşimleri, K vitamini eksikliği veya karaciğer hastalığı neden olabilir.",
    ),
    "blood.aptt": (
        "Kanın başka bir yoldan pıhtılaşmasının kaç saniye sürdüğünü ölçer. Kanama eğilimi araştırılırken ve heparin tedavisinin takibinde kullanılır.",
        "Kısa olması genellikle önemli değildir.",
        "Kan geç pıhtılaşıyordur. Heparin kullanımı, bazı kalıtsal pıhtılaşma faktörü eksiklikleri (hemofili gibi) veya karaciğer hastalığı uzatabilir. Nadiren kanda pıhtılaşmayı etkileyen antikorlar da neden olabilir.",
    ),
    "blood.d_dimer": (
        "Vücutta bir pıhtı oluşup çözülürken ortaya çıkan parçacıktır. Bacak damarında pıhtı veya akciğere pıhtı atması şüphesinde kullanılır.",
        "Normal (düşük) çıkması, pıhtı olasılığını büyük ölçüde azaltır. Testin asıl gücü budur.",
        "Vücutta bir yerde pıhtılaşma olduğunu gösterir ama nerede olduğunu söylemez. Ameliyat sonrası, gebelik, ileri yaş, enfeksiyon, yaralanma ve kanserde de yükselir; bu yüzden yüksek olması tek başına pıhtı olduğu anlamına gelmez, doktor gerekirse görüntüleme ister.",
    ),
    "blood.fibrinogen": (
        "Karaciğerde üretilen ve pıhtının ana yapısını oluşturan bir proteindir. Aynı zamanda iltihap sırasında da artar.",
        "Kanama eğilimi olabilir. İleri karaciğer hastalığı, kalıtsal eksiklikler veya pıhtılaşma faktörlerinin hızla tüketildiği ağır durumlarda düşer.",
        "Enfeksiyon, iltihap, gebelik, sigara ve ameliyat sonrasında yükselir. Uzun süreli yüksekliği kalp-damar riskiyle ilişkilendirilir.",
    ),
    # ---------------- İdrar ----------------
    "urine.color": (
        "İdrarın rengidir. Normalde açık sarı ile koyu sarı arasındadır; ne kadar su içildiğine göre değişir.",
        None,
        "Koyu sarı/turuncu: genelde az su içme veya bazı vitaminler. Kırmızı/pembe: kan, pancar veya bazı ilaçlar. Kahverengi/kola rengi: karaciğer sorunu veya ağır kas hasarı olabilir. Renk değişikliği birkaç gün sürüyorsa doktora danışılmalıdır.",
    ),
    "urine.clarity": (
        "İdrarın berrak mı bulanık mı olduğunu gösterir. Normalde berraktır.",
        None,
        "Bulanıklık; enfeksiyon (bakteri, iltihap hücreleri), kristaller, mukus veya idrarın bekletilmesiyle görülebilir. Tek başına teşhis koydurmaz; mikroskop sonuçlarıyla birlikte yorumlanır.",
    ),
    "urine.density": (
        "İdrarın ne kadar yoğun (konsantre) olduğunu gösterir; yani böbreklerin idrarı ne kadar koyulaştırdığını. Normalde yaklaşık 1,005–1,030 arasıdır.",
        "İdrar çok sulandırılmıştır; çok su içildiğinde normaldir. Sürekli düşük kalıyorsa böbreklerin idrarı yoğunlaştıramadığını gösterebilir.",
        "İdrar koyulaşmıştır; çoğunlukla az su içme, terleme, kusma veya ishal nedeniyle. İdrarda şeker veya protein olması da yükseltebilir.",
    ),
    "urine.ph": (
        "İdrarın asitlik derecesidir. Normalde hafif asidiktir (yaklaşık 5–7), ama beslenmeye göre değişir.",
        "İdrar asidiktir; çok proteinli (et ağırlıklı) beslenme, açlık, kontrolsüz şeker hastalığı veya susuzlukta görülür. Ürik asit taşı oluşumunu kolaylaştırabilir.",
        "İdrar bazik (alkali); sebze-meyve ağırlıklı beslenmede normaldir. Bazı idrar yolu enfeksiyonlarında veya idrarın uzun süre bekletilmesinde de görülür.",
    ),
    "urine.protein": (
        "İdrarda protein olup olmadığını gösterir. Sağlıklı böbrekler proteini kanda tutar, idrara geçirmez; normalde negatiftir.",
        None,
        "Böbreklerin süzgecinde hasar olabileceğini gösterir (şeker hastalığı ve yüksek tansiyon en sık nedenlerdir). Ancak ateş, yoğun egzersiz, stres ve uzun süre ayakta kalmak da geçici olarak pozitif yapabilir; doktor tekrar bakılmasını isteyebilir.",
    ),
    "urine.glucose": (
        "İdrarda şeker olup olmadığını gösterir. Kan şekeri belli bir seviyeyi (yaklaşık 180 mg/dL) aşınca böbrekler şekeri tutamaz ve idrara kaçar. Normalde negatiftir.",
        None,
        "En sık nedeni kan şekerinin yüksek olmasıdır (şeker hastalığı). Gebelikte ve bazı şeker ilaçlarını (SGLT2 grubu) kullananlarda kan şekeri normalken de pozitif olabilir.",
    ),
    "urine.ketone": (
        "Vücut enerji için şeker yerine yağ yaktığında oluşan maddelerdir. Normalde idrarda bulunmaz.",
        None,
        "Uzun açlık, çok düşük karbonhidratlı (ketojenik) diyet, kusma veya yoğun egzersiz sonrası görülebilir. Şeker hastalarında yüksek kan şekeriyle birlikte pozitif çıkması tehlikeli bir durumu (ketoasidoz) gösterebilir ve acil değerlendirme gerektirir.",
    ),
    "urine.bilirubin": (
        "Karaciğerde işlenen sarı renkli maddenin (bilirubin) idrarda olup olmadığını gösterir. Normalde negatiftir.",
        None,
        "Karaciğer hastalığı veya safra yollarında tıkanma olabileceğini gösterir. İdrar koyu çay rengi olabilir.",
    ),
    "urine.urobilinogen": (
        "Bilirubinin bağırsakta dönüştürülmesiyle oluşan ve az miktarda idrara geçen bir maddedir. Normalde az miktarda bulunur.",
        "Safra yollarının tamamen tıkandığı durumlarda veya antibiyotik kullanımında azalabilir.",
        "Karaciğer hastalığı veya kırmızı kan hücrelerinin hızlı yıkılması durumunda artabilir.",
    ),
    "urine.nitrite": (
        "Bazı bakteriler idrardaki maddeleri nitrite dönüştürür. Normalde negatiftir.",
        None,
        "İdrar yolu enfeksiyonunu düşündürür. Ancak negatif çıkması enfeksiyonu dışlamaz; bazı bakteriler nitrit üretmez ve idrar mesanede yeterince beklememişse sonuç negatif çıkabilir.",
    ),
    "urine.blood": (
        "Test çubuğuyla idrarda kan (hemoglobin) olup olmadığına bakılır. Normalde negatiftir.",
        None,
        "İdrar yolu enfeksiyonu, böbrek/idrar yolu taşı, yoğun egzersiz veya adet kanının karışması en sık nedenlerdir. Sürekli pozitif çıkıyorsa doktor nedenini araştırır. Kas hasarında da (miyoglobin) pozitif çıkabilir.",
    ),
    "urine.leukocyte_esterase": (
        "Test çubuğuyla idrarda beyaz kan hücresi (iltihap hücresi) olup olmadığına bakılır. Normalde negatiftir.",
        None,
        "İdrar yollarında iltihap veya enfeksiyon olduğunu düşündürür. Kadınlarda örnek alınırken vajinal akıntı karışması da pozitif yapabilir.",
    ),
    "urine.micro_rbc": (
        "İdrar mikroskopla incelendiğinde, büyük büyütmede bir alanda görülen kırmızı kan hücresi sayısıdır. Normalde 0–2 civarıdır.",
        "Düşük olması normaldir.",
        "İdrarda kan var demektir: idrar yolu enfeksiyonu, taş, yoğun egzersiz veya adet kanının karışması en sık nedenlerdir. Kalıcıysa doktor nedenini araştırır.",
    ),
    "urine.micro_wbc": (
        "İdrar mikroskopla incelendiğinde, büyük büyütmede bir alanda görülen beyaz kan hücresi (iltihap hücresi) sayısıdır. Normalde 0–5 civarıdır.",
        "Düşük olması normaldir.",
        "İdrar yollarında iltihap veya enfeksiyon olduğunu düşündürür. Örnek alırken temizlik yeterli değilse dışarıdan karışma da olabilir.",
    ),
    "urine.epithelium": (
        "İdrar yollarını ve dış genital bölgeyi döşeyen yüzey hücreleridir. Az miktarda görülmesi normaldir.",
        "Düşük olması normaldir.",
        "Çoğunlukla örneğin dış bölgeden kirlendiğini gösterir; temiz, orta akım idrarla tekrar alınması gerekebilir.",
    ),
    "urine.bacteria": (
        "İdrarda mikroskopla bakteri görülüp görülmediğidir. Normalde yok veya çok azdır.",
        None,
        "İdrar yolu enfeksiyonunu düşündürür, özellikle beyaz kan hücresi ve nitritle birlikte pozitifse. Ancak örnek dışarıdan kirlenmişse de görülebilir; kesin sonuç için idrar kültürü yapılır.",
    ),
    "urine.yeast": (
        "İdrarda mantar (maya) hücresi görülüp görülmediğidir. Normalde görülmez.",
        None,
        "Çoğunlukla vajinal mantar enfeksiyonunun örneğe karışmasıyla görülür. Şeker hastalarında, antibiyotik kullananlarda ve sonda takılı olanlarda daha sıktır.",
    ),
    "urine.crystal": (
        "İdrarda çözünemeyip katılaşan minerallerdir. Az miktarda görülmesi çoğu zaman normaldir.",
        None,
        "Az su içme, beslenme veya idrarın bekletilmesine bağlı olabilir. Bazı kristal türleri böbrek taşı yatkınlığını düşündürebilir; tekrar ediyorsa doktor değerlendirir.",
    ),
    "urine.cylinder": (
        "Böbrek kanalcıklarında şekillenip idrara dökülen küçük silindir şeklindeki yapılardır. Az sayıda şeffaf (hiyalin) silindir normal olabilir.",
        None,
        "Az sayıda şeffaf silindir egzersiz veya susuzluk sonrası görülebilir. Hücre içeren silindirler böbrek dokusunda bir sorun olabileceğini düşündürür ve doktor tarafından değerlendirilir.",
    ),
    "urine.mucus": (
        "İdrar yollarının salgıladığı kaygan maddedir. Az miktarda bulunması normaldir.",
        None,
        "Fazla miktarda olması genellikle örneğin dışarıdan kirlenmesiyle veya idrar yollarındaki tahrişle ilgilidir; tek başına çok anlam taşımaz.",
    ),
    "urine.culture": (
        "İdrar örneğinin laboratuvarda besiyerine ekilerek bakteri üreyip üremediğine bakılmasıdır. Enfeksiyona hangi bakterinin yol açtığını ve hangi antibiyotiğin işe yarayacağını gösterir. Sonuç genelde 2–3 günde çıkar.",
        None,
        "Belirli miktarın üstünde (genelde ≥100.000 koloni/mL) tek bir bakterinin üremesi idrar yolu enfeksiyonunu gösterir. Birden çok farklı bakteri ürediyse örnek büyük ihtimalle dışarıdan kirlenmiştir.",
    ),
    "urine.microalbumin": (
        "İdrardaki çok küçük miktarlardaki albümin (protein) kaçağını ölçer. Normal idrar tahlilinde görünmeyecek kadar erken böbrek hasarını yakalar; özellikle şeker ve tansiyon hastalarında yıllık bakılır.",
        "Düşük olması olumludur.",
        "Böbreğin süzgecinde erken bir hasar başlamış olabilir. Şeker hastalığı ve yüksek tansiyon en sık nedenlerdir. Yoğun egzersiz, ateş ve idrar yolu enfeksiyonu geçici olarak yükseltebilir; genellikle tekrar ölçümle doğrulanır.",
    ),
    # ---------------- Seroloji ----------------
    "serum.hbsag": (
        "Hepatit B virüsünün yüzeyindeki bir parçadır. Kanda olup olmadığına bakarak kişinin şu anda Hepatit B virüsü taşıyıp taşımadığı anlaşılır. Normalde negatiftir.",
        None,
        "Kişi Hepatit B virüsü taşıyor demektir (yeni geçirilen veya uzun süreli enfeksiyon). Mutlaka doktor tarafından takip edilmeli, aile bireyleri test edilip aşılanmalıdır.",
    ),
    "serum.anti_hbs": (
        "Hepatit B'ye karşı koruyucu antikordur. Aşıdan veya hastalığı geçirip iyileştikten sonra oluşur. Genellikle 10 mIU/mL ve üstü koruyucu kabul edilir.",
        "10'un altı Hepatit B'ye karşı korumanın yetersiz olduğunu gösterir; doktor aşı veya rapel önerebilir.",
        "Olumludur: kişi Hepatit B'ye karşı bağışıktır (aşı veya geçirilmiş ve iyileşmiş enfeksiyon sayesinde).",
    ),
    "serum.anti_hcv": (
        "Hepatit C virüsüne karşı oluşan antikordur. Kişinin hayatının herhangi bir döneminde Hepatit C virüsüyle karşılaşıp karşılaşmadığını gösterir. Normalde negatiftir.",
        None,
        "Virüsle karşılaşıldığını gösterir; ancak hâlâ aktif enfeksiyon olduğunu kanıtlamaz. Doktor virüsün kanda olup olmadığını görmek için ek test (HCV RNA) ister. Hepatit C günümüzde ilaçlarla büyük oranda tedavi edilebilmektedir.",
    ),
    "serum.anti_hiv": (
        "HIV virüsüne karşı oluşan antikorlara (ve çoğu testte virüsün bir parçasına) bakan tarama testidir. Normalde negatiftir.",
        None,
        "Tarama testinin pozitif çıkması kesin tanı değildir; yanlış pozitif olabilir. Mutlaka doğrulama testi yapılır. Doğrulanırsa erken başlanan tedaviyle normal bir yaşam sürdürülebilir.",
    ),
    "serum.vdrl": (
        "Frengi (sifiliz) hastalığı için yapılan bir tarama testidir. Normalde negatiftir (non-reaktif).",
        None,
        "Frengi enfeksiyonunu düşündürür ama gebelik, bazı bağışıklık hastalıkları ve başka enfeksiyonlar da yanlış pozitif yapabilir. Doktor doğrulama testi ister. Frengi antibiyotikle tedavi edilebilir.",
    ),
    "serum.aso": (
        "Streptokok adlı bakteriye karşı vücudun ürettiği bir antikordur. Kişinin yakın zamanda bu bakteriyle (sık olarak boğaz enfeksiyonu) karşılaştığını gösterir.",
        "Düşük olması normaldir.",
        "Yakın zamanda (birkaç hafta-ay içinde) streptokok enfeksiyonu geçirildiğini gösterir. Tek başına hastalık anlamına gelmez; çocuklarda sık görülür ve uzun süre yüksek kalabilir. Eklem ağrısı veya böbrek bulgularıyla birlikteyse doktor değerlendirir.",
    ),
    "serum.rf": (
        "Romatoid Faktör, bağışıklık sisteminin vücudun kendi proteinlerine karşı ürettiği bir antikordur. Romatoid artrit (iltihaplı eklem romatizması) araştırılırken bakılır.",
        "Düşük olması normaldir.",
        "Romatoid artriti düşündürebilir, ama sağlıklı insanlarda (özellikle yaşlılarda) ve bazı kronik enfeksiyonlarda da pozitif çıkabilir. Tek başına tanı koydurmaz; şikâyetler ve diğer testlerle birlikte değerlendirilir.",
    ),
    "blood.abo_rh": (
        "Kişinin kan grubunu (A, B, AB veya 0) ve Rh faktörünü (pozitif veya negatif) gösterir. Hayat boyu değişmez. Kan nakli ve gebelikte önemlidir.",
        None,
        "Rh negatif bir anne Rh pozitif bebek taşıyorsa gebelikte koruyucu iğne gerekebilir; bu yüzden gebelikte kan grubu mutlaka bilinmelidir.",
    ),
    # ---------------- Ölçümler ----------------
    "vital.weight": (
        "Vücut ağırlığıdır. Tek başına değil, boyla birlikte (vücut kitle indeksi) ve zaman içindeki değişimiyle anlamlıdır. Her gün aynı saatte, benzer kıyafetle tartılmak en doğru takibi sağlar.",
        "İstemeden ve belirgin kilo kaybı (6–12 ayda vücut ağırlığının %5'inden fazla) doktora danışılması gereken bir durumdur.",
        "Fazla kilo; tansiyon, şeker hastalığı, kolesterol, eklem sorunları ve uyku apnesi riskini artırır. Birkaç günde ani kilo artışı vücutta su birikmesine (ör. kalp veya böbrek sorunu) işaret edebilir.",
    ),
    "vital.bp_sys": (
        "Kalp kasıldığında damarlara uygulanan en yüksek basınçtır (büyük tansiyon). Genellikle 120'nin altı ideal kabul edilir. Ölçümden önce 5 dakika oturarak dinlenmek gerekir.",
        "Baş dönmesi, ayağa kalkınca kararma, halsizlik yapabilir. Susuzluk, tansiyon ilaçlarının fazla gelmesi veya uzun süre ayakta kalmak düşürebilir. Şikâyet yoksa düşük tansiyon genellikle sorun değildir.",
        "Tekrarlayan ölçümlerde 130–140 ve üstü yüksek tansiyon olarak değerlendirilir. Çoğu zaman belirti vermez ama yıllar içinde kalp, beyin, böbrek ve gözlere zarar verir. Tuz, fazla kilo, hareketsizlik, alkol ve stres yükseltir. 180 üstü ve baş ağrısı, göğüs ağrısı gibi şikâyetle birlikteyse acil başvurulmalıdır.",
    ),
    "vital.bp_dia": (
        "Kalp iki atım arasında gevşerken damarlarda kalan en düşük basınçtır (küçük tansiyon). Genellikle 80'in altı ideal kabul edilir.",
        "Tek başına düşük olması genellikle şikâyet yoksa önemli değildir; baş dönmesi varsa doktora danışılmalıdır.",
        "Tekrarlayan ölçümlerde 80–90 ve üstü yüksek tansiyon olarak değerlendirilir; özellikle gençlerde küçük tansiyon yüksekliği sık görülür. Uzun vadede kalp, beyin ve böbreklere zarar verebilir.",
    ),
    "vital.pulse": (
        "Kalbin dakikada kaç kez attığıdır. Dinlenirken yetişkinlerde normalde 60–100 arasındadır.",
        "Sporcularda ve düzenli egzersiz yapanlarda 60'ın altı normal olabilir. Baş dönmesi, bayılma hissi, halsizlik eşlik ediyorsa veya bazı kalp/tansiyon ilaçlarına bağlıysa doktora danışılmalıdır.",
        "Ateş, susuzluk, kansızlık, kaygı, kafein, tiroidin fazla çalışması veya kalp ritim sorunları yükseltebilir. Dinlenirken sürekli 100'ün üstünde olması veya düzensiz atım hissi doktora danışılmalıdır.",
    ),
    "vital.glucose_home": (
        "Evde parmaktan şeker ölçüm cihazıyla yapılan kan şekeri ölçümüdür. Açken, yemekten 2 saat sonra veya gerektiğinde yapılabilir; ölçüm zamanı not edilirse yorumlamak kolaylaşır.",
        "70'in altı düşük şekerdir: titreme, terleme, çarpıntı, baş dönmesi, dalgınlık yapabilir. Hızla şekerli bir şey (meyve suyu, şeker) alınmalıdır. 54'ün altı ciddi kabul edilir.",
        "Açken 100–125 sınırda, 126 ve üstü yüksek kabul edilir; yemekten 2 saat sonra genelde 140'ın altı beklenir. Şeker hastalarının hedefleri doktorlarıyla belirlenir. Ellerin temiz olmaması (meyve kalıntısı vb.) ölçümü yanlış yüksek gösterebilir.",
    ),
    "vital.temperature": (
        "Vücut sıcaklığıdır. Normalde yaklaşık 36–37,2 °C arasındadır; ölçüm yerine (koltuk altı, ağız, kulak) ve gün içinde biraz değişir.",
        "35 °C altı vücudun aşırı soğuduğunu gösterir; özellikle yaşlılarda ve bebeklerde önemlidir. Ölçüm hatası olup olmadığı kontrol edilmelidir.",
        "37,5–38 °C üstü ateş kabul edilir; çoğunlukla enfeksiyon belirtisidir. 39,5 °C üstü, 3 günden uzun süren ateş, bebeklerde ateş veya nefes darlığı/bilinç bulanıklığıyla birlikte olan ateşte doktora başvurulmalıdır.",
    ),
    "vital.spo2": (
        "Kandaki oksijen doygunluğudur; parmağa takılan cihazla (pulse oksimetre) ölçülür. Sağlıklı kişilerde genellikle %95–100 arasındadır.",
        "%92–94'ün altı kanda oksijenin azaldığını gösterir; nefes darlığı varsa doktora başvurulmalıdır. %90'ın altı acil durumdur. Soğuk eller, oje veya hareket ölçümü yanlış düşük gösterebilir.",
        "Yüksek olması sorun değildir; %100 normaldir.",
    ),
}

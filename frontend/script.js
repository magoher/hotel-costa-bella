/* ===============================================================
   script.js
   - Búsqueda de disponibilidad
   - Selección de habitación
   - Envío de reserva
   - Envío de formulario de contacto
   - Panel de administración (listar reservas en consola)
   =============================================================== */

const API = "/api"; 

document.addEventListener("DOMContentLoaded", () => {
  /* ---------- Referencias DOM ---------- */
  const searchForm      = document.getElementById("searchForm");
  const roomsTable      = document.getElementById("roomsTable");
  const tbody           = roomsTable.querySelector("tbody");
  const personalSection = document.getElementById("personalSection");
  const reservationForm = document.getElementById("reservationForm");
  const contactForm     = document.getElementById("contactForm");

  personalSection.classList.add("hidden");

  /* =========================================================== */
  /* 1) Búsqueda de disponibilidad                               */
  /* =========================================================== */
  searchForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const formData = new FormData(searchForm);
    const checkin  = formData.get("checkin");
    const checkout = formData.get("checkout");

    if (!checkin || !checkout) {
      alert("Selecciona fechas válidas");
      return;
    }
    if (new Date(checkout) <= new Date(checkin)) {
      alert("El check-out debe ser posterior al check-in");
      return;
    }

    roomsTable.classList.remove("hidden");
    roomsTable.scrollIntoView({ behavior: "smooth" });
  });

  /* =========================================================== */
  /* 2) Selección de habitación                                  */
  /* =========================================================== */
  window.selectRoom = (roomType /*, price */) => {
    const sf = new FormData(searchForm);
    reservationForm.elements["checkin"].value = sf.get("checkin");
    reservationForm.elements["checkout"].value = sf.get("checkout");
    reservationForm.elements["guests"].value = sf.get("guests");
    reservationForm.elements["roomType"].value = roomType;

    personalSection.classList.remove("hidden");
    personalSection.scrollIntoView({ behavior: "smooth" });
  };

  /* =========================================================== */
  /* 3) Envío de reserva                                         */
  /* =========================================================== */
  reservationForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(reservationForm).entries());

    const payload = {
      first_name: data.firstName,
      last_name : data.lastName,
      email     : data.email,
      phone     : data.phone,
      country   : data.country,
      city      : data.city,
      checkin_date : data.checkin,
      checkout_date: data.checkout,
      guests    : +data.guests,
      room_type : data.roomType,
      comments  : data.comments
    };

    try {
      const res = await fetch(`${API}/reservations`, {
        method : "POST",
        headers: { "Content-Type": "application/json" },
        body   : JSON.stringify(payload)
      });
      const json = await res.json();

      if (res.ok) {
        alert(`Reserva guardada ✅ (ID: ${json.reservation_id})`);
        reservationForm.reset();
        searchForm.reset();
        personalSection.classList.add("hidden");
        roomsTable.classList.add("hidden");
        window.scrollTo({ top: 0, behavior: "smooth" });
      } else {
        alert("Error al crear reserva: " + (json.detail || "desconocido"));
      }
    } catch (err) {
      console.error(err);
      alert("No se pudo conectar con el servidor");
    }
  });

  /* =========================================================== */
  /* 4) Formulario de contacto                                   */
  /* =========================================================== */
  if (contactForm) {
    contactForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = Object.fromEntries(new FormData(contactForm).entries());

      try {
        const res = await fetch(`${API}/contact`, {
          method : "POST",
          headers: { "Content-Type": "application/json" },
          body   : JSON.stringify(payload)
        });
        if (res.ok) {
          alert("¡Mensaje enviado! 💌");
          contactForm.reset();
        } else {
          alert("Error al enviar mensaje");
        }
      } catch (err) {
        console.error(err);
        alert("No se pudo conectar con el servidor");
      }
    });
  }

  /* =========================================================== */
  /* 6) Weather API Integration                                  */
  /* =========================================================== */
  
  async function loadWeatherData() {
    const weatherCard = document.querySelector('#weather #weatherCard');
    
    if (!weatherCard) {
      console.log("⚠️ Weather card not found");
      return;
    }
    
    try {
      console.log("🌤️ Cargando datos del clima...");
      
      // Intentar obtener datos del clima desde el backend
      const response = await fetch(`${API}/api/weather/San José`);
      
      if (response.ok) {
        const weatherData = await response.json();
        displayWeatherData(weatherData);
        console.log("✅ Datos del clima cargados:", weatherData);
      } else {
        // Si falla, mostrar datos demo
        console.log("⚠️ API del clima no disponible, usando datos demo");
        showDemoWeather();
      }
    } catch (error) {
      console.error("❌ Error cargando clima:", error);
      showDemoWeather();
    }
  }
  
  function displayWeatherData(data) {
    renderGridFromWeatherObject(data);
  }
  
  function showDemoWeather() {
    const weatherCard = document.querySelector('#weather #weatherCard');
    
    if (!weatherCard) return;
    
    weatherCard.innerHTML = `
      <div class="weather-main">
        <div class="weather-temp">25°C</div>
        <div class="weather-icon">🌤️</div>
      </div>
      <div class="weather-desc">Parcialmente nublado</div>
      <div class="weather-details">
        <div class="weather-detail">
          <span>💧 Humedad</span>
          <strong>78%</strong>
        </div>
        <div class="weather-detail">
          <span>📍 Ciudad</span>
          <strong>San José</strong>
        </div>
      </div>
      <div class="weather-timestamp">
        Datos demo - ${new Date().toLocaleString('es-ES')}
      </div>
    `;
  }
  
  function getWeatherIcon(description) {
    const desc = description.toLowerCase();
    
    if (desc.includes('sol') || desc.includes('despejado') || desc.includes('clear')) {
      return '☀️';
    } else if (desc.includes('nub') || desc.includes('cloud')) {
      return '⛅';
    } else if (desc.includes('lluv') || desc.includes('rain')) {
      return '🌧️';
    } else if (desc.includes('tormenta') || desc.includes('storm')) {
      return '⛈️';
    } else if (desc.includes('nieve') || desc.includes('snow')) {
      return '❄️';
    } else if (desc.includes('niebla') || desc.includes('fog')) {
      return '🌫️';
    } else {
      return '🌤️';
    }
  }

  /* =========================================================== */
  /* 7) Weather and Province Selection                           */
  /* =========================================================== */
  
  // Datos de las provincias de Costa Rica
  const provinceData = {
    "San José": {
      city: "San José",
      lat: 9.9281,
      lon: -84.0907,
      capital: true,
      climate: "Templado tropical",
      altitude: "1170 m",
      population: "2.1 millones",
      benefits: [
        "🏛️ Centro cultural y comercial del país",
        "🌡️ Clima templado todo el año (20-26°C)",
        "🚗 Fácil acceso a otras provincias",
        "🏛️ Museos, teatros y vida nocturna",
        "🏥 Mejores servicios médicos del país"
      ]
    },
    "Alajuela": {
      city: "Alajuela",
      lat: 10.0162,
      lon: -84.2118,
      capital: false,
      climate: "Tropical seco",
      altitude: "952 m",
      population: "1 millón",
      benefits: [
        "✈️ Aeropuerto Internacional Juan Santamaría",
        "🌋 Volcán Poás y Volcán Arenal cercanos",
        "🌱 Zona agrícola muy fértil",
        "🌡️ Clima cálido y seco",
        "🏞️ Parques nacionales y naturaleza"
      ]
    },
    "Cartago": {
      city: "Cartago",
      lat: 9.8644,
      lon: -83.9186,
      capital: false, 
      climate: "Templado húmedo",
      altitude: "1435 m",
      population: "490,000",
      benefits: [
        "⛪ Basílica de los Ángeles (Virgen de los Ángeles)",
        "🌋 Volcán Irazú - punto más alto del país",
        "🌡️ Clima fresco y agradable",
        "🏛️ Primera capital de Costa Rica",
        "🌿 Valle Central muy fértil"
      ]
    },
    "Heredia": {
      city: "Heredia",
      lat: 9.9989,
      lon: -84.1174,
      capital: false,
      climate: "Templado",
      altitude: "1150 m", 
      population: "433,000",
      benefits: [
        "🎓 Ciudad universitaria (UNA)",
        "☕ Región cafetera por excelencia",
        "🌳 Parque Nacional Braulio Carrillo",
        "🌡️ Clima ideal para el café",
        "🏞️ Cercanía a San José y naturaleza"
      ]
    },
    "Guanacaste": {
      city: "Liberia",
      lat: 10.6346,
      lon: -85.4370,
      capital: false,
      climate: "Tropical seco",
      altitude: "144 m",
      population: "326,000",
      benefits: [
        "🏖️ Mejores playas del Pacífico",
        "☀️ Sol y playa todo el año", 
        "🐎 Cultura ganadera y folclore",
        "🌮 Gastronomía típica costarricense",
        "🏄‍♂️ Surf y deportes acuáticos"
      ]
    },
    "Puntarenas": {
      city: "Puntarenas",
      lat: 9.9761,
      lon: -84.8303,
      capital: false,
      climate: "Tropical húmedo",
      altitude: "3 m",
      population: "410,000", 
      benefits: [
        "🚢 Puerto principal del Pacífico",
        "🏖️ Playas de arena oscura volcánica",
        "🐋 Avistamiento de ballenas",
        "🎣 Pesca deportiva",
        "🌴 Islas del Golfo de Nicoya"
      ]
    },
    "Limón": {
      city: "Puerto Limón",
      lat: 10.0000,
      lon: -83.0333,
      capital: false,
      climate: "Tropical húmedo",
      altitude: "5 m",
      population: "386,000",
      benefits: [
        "🌊 Costa del Caribe costarricense",
        "🥥 Playas de arena blanca y cocoteros",
        "🎵 Cultura afrocaribeña y reggae",
        "🦥 Parque Nacional Tortuguero",
        "🐢 Anidación de tortugas marinas"
      ]
    }
  };
  
  // Función para cambiar provincia
  window.changeProvince = async function() {
    const select = document.getElementById('provinceSelect');
    const selectedProvince = select.value;
    const provinceInfo = provinceData[selectedProvince];
    
    console.log(`🏛️ Cambiando a provincia: ${selectedProvince}`);
    
    // Actualizar información de beneficios
    updateProvinceBenefits(selectedProvince, provinceInfo);
    
    // Cargar datos del clima para la nueva ciudad
    await loadWeatherForCity(provinceInfo.city);
  };
  
  function updateProvinceBenefits(provinceName, info) {
    const benefitsDiv = document.getElementById('provinceBenefits');
    const titleDiv = document.getElementById('currentProvinceTitle');
    if (titleDiv && info) {
      titleDiv.textContent = `Provincia: ${provinceName} — Ciudad: ${info.city}`;
    }
    if (!benefitsDiv) return;
    
    // Información específica por provincia
    const provinceInfo = {
      "San José": {
        icon: "🏛️",
        title: "San José (Central)",
        benefits: [
          "🌡️ Clima templado todo el año (18-26°C)",
          "🏛️ Centro cultural y comercial del país",
          "🚗 Fácil acceso a otras provincias",
          "🏥 Mejores servicios médicos y educativos"
        ]
      },
      "Alajuela": {
        icon: "✈️",
        title: "Alajuela",
        benefits: [
          "☀️ Clima cálido y soleado (20-30°C)",
          "✈️ Cerca del Aeropuerto Internacional",
          "🌋 Volcán Arenal y aguas termales",
          "🍃 Rica biodiversidad y ecoturismo"
        ]
      },
      "Cartago": {
        icon: "⛪",
        title: "Cartago",
        benefits: [
          "🌤️ Clima fresco de montaña (15-22°C)",
          "⛪ Rica historia colonial y religiosa",
          "🏔️ Volcán Irazú y paisajes montañosos",
          "🌿 Agricultura de altura y café"
        ]
      },
      "Heredia": {
        icon: "🎓",
        title: "Heredia",
        benefits: [
          "🌤️ Clima ideal para vivir (18-25°C)",
          "🎓 Ciudad universitaria y educativa",
          "🌲 Cerca de bosques nubosos",
          "☕ Excelente café de montaña"
        ]
      },
      "Guanacaste": {
        icon: "🏖️",
        title: "Liberia (Guanacaste)",
        benefits: [
          "☀️ Clima seco y soleado (25-35°C)",
          "🏖️ Mejores playas del Pacífico",
          "🐴 Cultura ganadera tradicional",
          "🌅 Perfecto para turismo de sol y playa"
        ]
      },
      "Puntarenas": {
        icon: "🌊",
        title: "Puntarenas",
        benefits: [
          "🌊 Clima tropical costero (24-32°C)",
          "⛵ Puerto principal del Pacífico",
          "🐋 Avistamiento de ballenas",
          "🎣 Pesca deportiva de clase mundial"
        ]
      },
      "Limón": {
        icon: "🌴",
        title: "Puerto Limón",
        benefits: [
          "🌴 Clima caribeño húmedo (22-30°C)",
          "🏝️ Playas del Caribe costarricense",
          "🦥 Parques nacionales únicos",
          "🎵 Rica cultura afro-caribeña"
        ]
      }
    };
    
    const info_data = provinceInfo[provinceName] || provinceInfo["San José"];
    
    benefitsDiv.innerHTML = `
      <h4>${info_data.icon} ${info_data.title}</h4>
      <ul style="list-style: none; padding-left: 0;">
        ${info_data.benefits.map(benefit => `<li style="margin: 0.5rem 0; padding: 0.25rem 0;">${benefit}</li>`).join('')}
      </ul>
    `;
  }
  
  function renderGridFromWeatherObject(obj){
    // obj can be backend WeatherResponse or demo
    const cards = [
      { id: 'weather1', title: 'Temperatura', value: `${Math.round(obj.temperature ?? obj.temp ?? 0)}°C`, desc: obj.description ?? obj.desc ?? '—', icon: getWeatherIcon((obj.description ?? obj.desc ?? '').toString()) },
      { id: 'weather2', title: 'Humedad', value: `${obj.humidity ?? 0}%`, desc: 'Nivel de humedad', icon: '💧' },
      { id: 'weather3', title: 'Viento', value: `${obj.windSpeed ?? 10} km/h`, desc: 'Velocidad del viento', icon: '🌬️' },
      { id: 'weather4', title: 'Sensación', value: `${Math.round((obj.feels_like ?? obj.feels ?? (obj.temperature ?? obj.temp ?? 0)+2))}°C`, desc: 'Sensación térmica', icon: '🌡️' },
    ];
    for (const c of cards){
      const el = document.getElementById(c.id);
      if (!el) continue;
      el.innerHTML = `
        <div style="display:flex; align-items:center; justify-content:space-between; gap:0.4rem;">
          <div style="font-size:1.4rem; line-height:1">${c.icon}</div>
          <div style="text-align:right">
            <div style="color:#64748b; font-size:.8rem;">${c.title}</div>
            <div style="color:#111827; font-size:1.6rem; font-weight:800;">${c.value}</div>
            <div style="color:#6b7280; font-size:.75rem;">${c.desc}</div>
          </div>
        </div>`;
    }
  }

  // Override display to use 2x2 grid
  function displayWeatherData(data) {
    renderGridFromWeatherObject(data);
  }

  function showDemoWeatherForCity(cityName) {
    const demoData = {
      "San José": { temp: 24, desc: "Parcialmente nublado", humidity: 73, icon: "⛅", windSpeed: 8, visibility: 12, feels: 26 },
      "Alajuela": { temp: 27, desc: "Soleado y despejado", humidity: 68, icon: "☀️", windSpeed: 12, visibility: 15, feels: 30 },
      "Cartago": { temp: 20, desc: "Fresco y nublado", humidity: 82, icon: "☁️", windSpeed: 6, visibility: 8, feels: 18 },
      "Heredia": { temp: 22, desc: "Templado y agradable", humidity: 78, icon: "🌤️", windSpeed: 10, visibility: 10, feels: 24 },
      "Liberia": { temp: 32, desc: "Caluroso y seco", humidity: 55, icon: "☀️", windSpeed: 15, visibility: 18, feels: 35 },
      "Puntarenas": { temp: 29, desc: "Húmedo y cálido", humidity: 85, icon: "🌊", windSpeed: 14, visibility: 12, feels: 33 },
      "Puerto Limón": { temp: 28, desc: "Tropical húmedo", humidity: 88, icon: "🌴", windSpeed: 11, visibility: 9, feels: 32 }
    };
    const demo = demoData[cityName] || demoData["San José"];
    renderGridFromWeatherObject(demo);
  }

  async function loadWeatherForCity(cityName) {
    const grid = document.getElementById('weatherGrid');
    if (grid){
      grid.querySelectorAll('.weather-card-item').forEach(c => c.innerHTML = '<div class="weather-loading">🔄 Cargando...</div>');
    }
    try {
      const response = await fetch(`${API}/api/weather/${encodeURIComponent(cityName)}`);
      if (response.ok) {
        const weatherData = await response.json();
        renderGridFromWeatherObject(weatherData);
      } else {
        showDemoWeatherForCity(cityName);
      }
    } catch (e) {
      showDemoWeatherForCity(cityName);
    }
  }

  // Initialize title on first load inside changeProvince call
  changeProvince();
  
  // Actualizar clima cada 10 minutos
  setInterval(() => {
    const select = document.getElementById('provinceSelect');
    const selectedProvince = select.value;
    const provinceInfo = provinceData[selectedProvince];
    loadWeatherForCity(provinceInfo.city);
  }, 600000);

  // Nota: Los botones de Dashboard y Admin ahora están en la navegación principal
});

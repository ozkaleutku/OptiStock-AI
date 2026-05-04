import axios from 'axios';

const backendPort = import.meta.env.VITE_BACKEND_PORT || 8000;

const api = axios.create({
    // Backend portunu .env den al (yoksa varsayilan 8000)
    baseURL: `http://${window.location.hostname}:${backendPort}/api`,
});

export default api;

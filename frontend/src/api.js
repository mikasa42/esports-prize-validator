import axios from 'axios';

axios.defaults.withCredentials = true;
axios.defaults.headers.common['X-Requested-With'] = 'TournamentHub';
export const API_URL = process.env.REACT_APP_API_URL || '';
export default axios;

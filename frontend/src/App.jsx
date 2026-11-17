import { useEffect, useState } from "react";
import { ensureCsrfCookie, fetchMe } from "./api.js";
import LoginScreen from "./LoginScreen.jsx";
import SettingsScreen from "./SettingsScreen.jsx";

export default function App() {
  const [me, setMe] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        await ensureCsrfCookie(); // sets the csrftoken cookie needed for login/logout/etc
        const response = await fetchMe();
        if (response.ok) setMe(response.data);
      } catch (error) {
        // fetch() rejects on a network-level failure (backend not running,
        // CORS blocked, etc) rather than resolving with an error status -
        // without this, that left the app stuck on "Loading..." forever.
        setLoadError(error.message);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <p>Loading...</p>;

  if (loadError) {
    return (
      <div>
        <p>Couldn't reach the backend: {loadError}</p>
        <p>Is `manage.py runserver` running at the API base URL in frontend/.env?</p>
      </div>
    );
  }

  if (!me) return <LoginScreen onLoggedIn={setMe} />;

  return <SettingsScreen me={me} onUpdated={setMe} onLoggedOut={() => setMe(null)} />;
}

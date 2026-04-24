importScripts("https://www.gstatic.com/firebasejs/10.10.0/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.10.0/firebase-messaging-compat.js");

firebase.initializeApp({
  apiKey: 'AIzaSyBPfLgiwhQ66L8P32jY0VADw0cNWmcfUIg',
  authDomain: 'mma-project-91699.firebaseapp.com',
  databaseURL: 'https://mma-project-91699-default-rtdb.europe-west1.firebasedatabase.app',
  projectId: 'mma-project-91699',
  storageBucket: 'mma-project-91699.firebasestorage.app',
  messagingSenderId: '826115118753',
  appId: '1:826115118753:web:97e82a487b3e7b7c0f82e0',
});


const messaging = firebase.messaging();

messaging.onBackgroundMessage(function(payload) {
  const data = payload.data;

  return clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
    let isFocused = false;
    let isAnyWindowOpen = false;

    for (let i = 0; i < windowClients.length; i++) {
      isAnyWindowOpen = true;
      if (windowClients[i].visibilityState === 'visible') {
        isFocused = true;
        break;
      }
    }

    // 1. ZAVŘENO: Pokud neexistuje žádné okno aplikace, nedělej nic (neotravujeme!)
    if (!isAnyWindowOpen) return null;

    // 2. OTEVŘENO: Pokud uživatel aplikaci vidí, Flutter si sám vyhodí Toast (SnackBar). SW nedělá nic.
    if (isFocused) return null;

    // 3. V POZADÍ: Aplikace běží, ale v jiném tabu. Zobrazíme systémovou notifikaci ručně.
    return self.registration.showNotification(data.title, {
      body: data.body,
      icon: '/icons/Icon-192.png',
      data: data
    });
  });
});
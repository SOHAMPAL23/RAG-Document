// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyBRFqCgLgFAM8SX5bQVoOr2MDd-9hPVzS4",
  authDomain: "ragdocument-ec9a6.firebaseapp.com",
  projectId: "ragdocument-ec9a6",
  storageBucket: "ragdocument-ec9a6.firebasestorage.app",
  messagingSenderId: "599025986360",
  appId: "1:599025986360:web:223140d6394f2104326fcd",
  measurementId: "G-6HB65D1C1P"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);
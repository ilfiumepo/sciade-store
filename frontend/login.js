const loginForm = document.querySelector("[data-login-form]");
const loginMessage = document.querySelector("[data-login-message]");
const submitButton = document.querySelector("[data-auth-submit]");
const signupFields = document.querySelector("[data-signup-fields]");
const modeInput = loginForm.elements.mode;
const nextPage = new URLSearchParams(window.location.search).get("next");

document.querySelectorAll("[data-auth-mode]").forEach((button) => {
  button.addEventListener("click", () => {
    const mode = button.dataset.authMode;
    const isSignup = mode === "signup";
    modeInput.value = mode;
    submitButton.textContent = isSignup ? "Crea account" : "Accedi";
    signupFields.classList.toggle("is-hidden", !isSignup);
    loginForm.elements.firstName.required = isSignup;
    loginForm.elements.lastName.required = isSignup;
    loginForm.elements.birthdate.required = isSignup;
    loginForm.elements.password.autocomplete = isSignup ? "new-password" : "current-password";
    loginMessage.textContent = "";
    document.querySelectorAll("[data-auth-mode]").forEach((tab) => {
      tab.classList.toggle("is-active", tab === button);
    });
  });
});

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  const mode = formData.get("mode");

  loginMessage.textContent = mode === "signup" ? "Creazione account..." : "Controllo account...";
  loginMessage.style.color = "#6b625d";

  try {
    const response = await fetch(mode === "signup" ? "/api/signup" : "/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: formData.get("email"),
        firstName: formData.get("firstName"),
        lastName: formData.get("lastName"),
        birthdate: formData.get("birthdate"),
        password: formData.get("password"),
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || "Accesso non riuscito");
    }
    const result = await response.json();
    if (nextPage && result.role !== "admin") {
      window.location.href = nextPage;
      return;
    }
    window.location.href = result.redirectTo || "/index.html";
  } catch (error) {
    loginMessage.textContent = error.message || "Accesso non riuscito.";
    loginMessage.style.color = "#bc5965";
  }
});

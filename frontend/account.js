const profileForm = document.querySelector("[data-profile-form]");
const passwordForm = document.querySelector("[data-password-form]");
const profileMessage = document.querySelector("[data-profile-message]");
const passwordMessage = document.querySelector("[data-password-message]");
const logoutButton = document.querySelector("[data-logout]");

function setMessage(element, text, isError = false) {
  element.textContent = text;
  element.style.color = isError ? "#bc5965" : "#26716f";
}

async function loadAccount() {
  const response = await fetch("/api/account");
  if (!response.ok) {
    window.location.href = "/login.html";
    return;
  }

  const data = await response.json();
  const user = data.user;
  profileForm.elements.email.value = user.email || "";
  profileForm.elements.firstName.value = user.firstName || "";
  profileForm.elements.lastName.value = user.lastName || "";
  profileForm.elements.birthdate.value = user.birthdate || "";
}

profileForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  setMessage(profileMessage, "Salvataggio dati...");

  try {
    const response = await fetch("/api/account", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        firstName: formData.get("firstName"),
        lastName: formData.get("lastName"),
        birthdate: formData.get("birthdate"),
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || "Impossibile salvare i dati dell'account.");
    }

    const data = await response.json();
    profileForm.elements.firstName.value = data.user.firstName || "";
    profileForm.elements.lastName.value = data.user.lastName || "";
    profileForm.elements.birthdate.value = data.user.birthdate || "";
    setMessage(profileMessage, "Dati salvati.");
  } catch (error) {
    setMessage(profileMessage, error.message || "Impossibile salvare i dati.", true);
  }
});

passwordForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(event.currentTarget);
  setMessage(passwordMessage, "Cambio password...");

  try {
    const response = await fetch("/api/account/password", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        currentPassword: formData.get("currentPassword"),
        newPassword: formData.get("newPassword"),
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || "Impossibile cambiare la password.");
    }

    passwordForm.reset();
    setMessage(passwordMessage, "Password cambiata.");
  } catch (error) {
    setMessage(passwordMessage, error.message || "Impossibile cambiare la password.", true);
  }
});

logoutButton.addEventListener("click", async () => {
  await fetch("/api/logout", { method: "POST" });
  window.location.href = "/index.html";
});

loadAccount();

// File Sharing Module
let currentFileId = null;
let currentFileName = null;

async function openShareDialog(fileId, fileName) {
  currentFileId = fileId;
  currentFileName = fileName;

  // Create or get modal
  let shareModal = document.getElementById("shareModal");
  if (!shareModal) {
    const modalHtml = `
      <div class="modal fade" id="shareModal" tabindex="-1">
        <div class="modal-dialog modal-lg">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">Share: <span id="shareFileName"></span></h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
              <div id="shareContent">
                <!-- Share form -->
                <div class="mb-4">
                  <h6>Share with people</h6>
                  <div class="input-group mb-3">
                    <input
                      type="email"
                      class="form-control"
                      id="shareEmail"
                      placeholder="Enter email address"
                    />
                    <select class="form-select" id="shareRole" style="max-width: 150px;">
                      <option value="reader">Viewer</option>
                      <option value="commenter">Commenter</option>
                      <option value="writer">Editor</option>
                    </select>
                    <button class="btn btn-primary" onclick="addShare()">
                      <i class="bi bi-plus"></i> Share
                    </button>
                  </div>
                  <small class="text-muted">
                    • <strong>Viewer:</strong> Can view only
                    • <strong>Commenter:</strong> Can view and comment
                    • <strong>Editor:</strong> Can view, edit, and share
                  </small>
                </div>

                <!-- Current shares list -->
                <div class="mb-4">
                  <h6>People with access</h6>
                  <div id="sharesList" style="max-height: 300px; overflow-y: auto;"></div>
                </div>

                <!-- Error messages -->
                <div id="shareError" style="display: none;"></div>
              </div>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
            </div>
          </div>
        </div>
      </div>
    `;
    document.body.insertAdjacentHTML("beforeend", modalHtml);
    shareModal = document.getElementById("shareModal");
  }

  // Update filename
  document.getElementById("shareFileName").textContent = fileName;

  // Load current shares
  await loadCurrentShares();

  // Show modal
  const modal = new bootstrap.Modal(shareModal);
  modal.show();
}

async function loadCurrentShares() {
  try {
    const response = await apiClient.get(`/files/${currentFileId}/`);
    const file = response.data;

    // Get permissions
    const permResponse = await apiClient.get(
      `/permissions/?file=${currentFileId}`,
    );
    const permissions = permResponse.data.results || [];

    const sharesList = document.getElementById("sharesList");

    if (permissions.length === 0) {
      sharesList.innerHTML =
        '<p class="text-muted">Not shared with anyone yet</p>';
      return;
    }

    sharesList.innerHTML = permissions
      .map((perm) => {
        const email =
          perm.grantee_email || perm.grantee_user_email || "Unknown";
        const role = perm.role;
        return `
        <div class="d-flex justify-content-between align-items-center p-2 border-bottom">
          <div>
            <div style="font-weight: 500;">${email}</div>
            <small class="text-muted">${getRoleLabel(role)}</small>
          </div>
          <button class="btn btn-sm btn-outline-danger" onclick="removeShare('${perm.id}')">
            <i class="bi bi-trash"></i> Remove
          </button>
        </div>
      `;
      })
      .join("");
  } catch (error) {
    console.error("Error loading shares:", error);
    showShareError(
      "Failed to load shares: " +
        (error.response?.data?.detail || error.message),
    );
  }
}

function getRoleLabel(role) {
  const roles = {
    reader: "Can view",
    commenter: "Can comment",
    writer: "Can edit",
    owner: "Owner",
    organizer: "Organizer",
  };
  return roles[role] || role;
}

async function addShare() {
  const email = document.getElementById("shareEmail").value.trim();
  const role = document.getElementById("shareRole").value;

  if (!email) {
    showShareError("Please enter an email address");
    return;
  }

  if (!email.includes("@")) {
    showShareError("Please enter a valid email address");
    return;
  }

  try {
    const response = await apiClient.post("/permissions/", {
      file: currentFileId,
      grantee_email: email,
      permission_type: "user",
      role: role,
    });

    // Clear input
    document.getElementById("shareEmail").value = "";

    // Reload shares list
    await loadCurrentShares();

    showShareSuccess(`Shared with ${email} (${getRoleLabel(role)})`);
  } catch (error) {
    console.error("Error adding share:", error);
    const errorMsg =
      error.response?.data?.detail ||
      error.response?.data?.grantee_email?.[0] ||
      error.response?.data?.non_field_errors?.[0] ||
      error.message;
    showShareError("Failed to share: " + errorMsg);
  }
}

async function removeShare(permissionId) {
  if (!confirm("Remove this person's access?")) {
    return;
  }

  try {
    await apiClient.delete(`/permissions/${permissionId}/`);
    await loadCurrentShares();
    showShareSuccess("Access removed");
  } catch (error) {
    console.error("Error removing share:", error);
    showShareError("Failed to remove access: " + error.message);
  }
}

function showShareError(message) {
  const errorDiv = document.getElementById("shareError");
  errorDiv.innerHTML = `
    <div class="alert alert-danger alert-dismissible fade show" role="alert">
      <i class="bi bi-exclamation-circle"></i> ${message}
      <button type="button" class="btn-close" onclick="this.parentElement.style.display='none'"></button>
    </div>
  `;
  errorDiv.style.display = "block";
}

function showShareSuccess(message) {
  const errorDiv = document.getElementById("shareError");
  errorDiv.innerHTML = `
    <div class="alert alert-success alert-dismissible fade show" role="alert">
      <i class="bi bi-check-circle"></i> ${message}
      <button type="button" class="btn-close" onclick="this.parentElement.style.display='none'"></button>
    </div>
  `;
  errorDiv.style.display = "block";

  // Auto-hide after 3 seconds
  setTimeout(() => {
    errorDiv.style.display = "none";
  }, 3000);
}

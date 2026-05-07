import { getToken } from '/static/js/auth.js';

export async function setupCommentImageUpload() {
    const uploadBtn = document.getElementById('uploadCommentImageBtn');
    const imageInput = document.getElementById('commentImageInput');
    const imagePreview = document.getElementById('commentImagePreview');
    let currentImageUrl = null;

    if (!uploadBtn) return;

    uploadBtn.addEventListener('click', () => {
        imageInput.click();
    });

    imageInput.addEventListener('change', async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        if (!file.type.startsWith('image/')) {
            alert('Please select an image file.');
            return;
        }
        if (file.size > 5 * 1024 * 1024) {
            alert('File too large. Maximum size is 5MB.');
            return;
        }

        const token = getToken();
        if (!token) {
            window.location.href = '/login';
            return;
        }

        // Show loading state
        uploadBtn.disabled = true;
        uploadBtn.textContent = 'Uploading Please Wait...';

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/uploads/comment-image', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                },
                body: formData,
            });

            if (response.status === 401) {
                window.location.href = '/login';
                return;
            }

            if (response.ok) {
                const data = await response.json();
                currentImageUrl = data.url;
                
                imagePreview.innerHTML = `
                    <div class="position-relative d-inline-block">
                        <img src="${currentImageUrl}" alt="Preview" class="img-thumbnail" style="max-height: 100px;">
                        <button type="button" class="btn btn-sm btn-danger position-absolute top-0 end-0" id="removeImageBtn">×</button>
                    </div>
                `;
                
                document.getElementById('removeImageBtn')?.addEventListener('click', () => {
                    currentImageUrl = null;
                    imagePreview.innerHTML = '';
                    imageInput.value = '';
                });
            } else {
                const error = await response.json();
                alert(error.detail || 'Upload failed');
            }
        } catch (error) {
            console.error('Upload error:', error);
            alert('Network error. Please try again.');
        } finally {
            uploadBtn.disabled = false;
            uploadBtn.textContent = '📷 Upload Image';
        }
    });

    return {
        getImageUrl: () => currentImageUrl,
        clearImage: () => {
            currentImageUrl = null;
            imagePreview.innerHTML = '';
            imageInput.value = '';
        }
    };
}
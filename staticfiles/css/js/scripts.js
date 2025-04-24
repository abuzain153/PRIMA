const productSearchInput = document.getElementById('product-search-input');
    const toggleProductListButton = document.getElementById('toggle-product-list');
    const productSuggestionsList = document.getElementById('product-suggestions');
    const selectedProductIdInput = document.getElementById('selected-product-id');
    const productNameInput = document.getElementById('product_name');
    const unitInput = document.getElementById('unit');
    const availableQuantityInput = document.getElementById('available_quantity');

    let isListVisible = false;

    toggleProductListButton.addEventListener('click', function() {
        isListVisible = !isListVisible;
        productSuggestionsList.style.display = isListVisible ? 'block' : 'none';
        // شيلنا التحميل الأولي هنا
    });

    productSearchInput.addEventListener('input', function() {
        const searchText = this.value.trim();
        if (searchText) {
            fetchProducts(searchText);
            productSuggestionsList.style.display = 'block';
            isListVisible = true;
        } else if (!isListVisible) {
            productSuggestionsList.style.display = 'none';
        } else if (searchText === '' && isListVisible) {
            productSuggestionsList.style.display = 'none';
            isListVisible = false;
        }
    });

    function fetchProducts(searchText) {
        fetch(`/products/get_products_by_name/?name=${searchText}`)
            .then(response => response.json())
            .then(data => {
                productSuggestionsList.innerHTML = '';
                data.forEach(product => {
                    const listItem = document.createElement('a');
                    listItem.classList.add('list-group-item', 'list-group-item-action');
                    listItem.textContent = `${product.product_name} (${product.product_code})`;
                    listItem.dataset.productId = product.id;
                    listItem.dataset.productName = product.product_name;
                    listItem.dataset.unit = product.unit || '';
                    listItem.dataset.available = product.quantity || ''; // Use 'quantity' from your view
                    listItem.addEventListener('click', function() {
                        productSearchInput.value = this.dataset.productName;
                        selectedProductIdInput.value = this.dataset.productId;
                        productNameInput.value = this.dataset.productName;
                        unitInput.value = this.dataset.unit || '';
                        availableQuantityInput.value = this.dataset.available || '';
                        productSuggestionsList.style.display = 'none';
                        isListVisible = false;
                    });
                    productSuggestionsList.appendChild(listItem);
                });
                if (data.length === 0 && searchText) {
                    const listItem = document.createElement('a');
                    listItem.classList.add('list-group-item', 'list-group-item-action', 'disabled');
                    listItem.textContent = '{% translate "لا يوجد منتجات مطابقة" %}';
                    productSuggestionsList.appendChild(listItem);
                }
            });
    }

    // Hide suggestions list on blur (when focus is lost from the input)
    productSearchInput.addEventListener('blur', function() {
        // Use a small delay to allow click on suggestion
        setTimeout(() => {
            if (!productSuggestionsList.matches(':hover')) {
                productSuggestionsList.style.display = 'none';
                isListVisible = false;
            }
        }, 200);
    });

    // Prevent form submission on Enter key in search input
    productSearchInput.addEventListener('keydown', function(event) {
        if (event.key === 'Enter') {
            event.preventDefault();
        }
    });
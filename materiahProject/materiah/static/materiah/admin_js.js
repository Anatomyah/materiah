(function ($) {
  console.log("Script loaded");
  window.updateProductChoices = function (selectElement) {
    console.log("updateProductChoices called");
    let supplierId = selectElement.value;
    console.log("Selected Supplier ID: ", supplierId);
    let xhr = new XMLHttpRequest();
    xhr.open(
      "GET",
      `materiah/admin/get_products_by_supplier/${supplierId}/`,
      true,
    );
    xhr.onreadystatechange = function () {
      // console.log("Server Response: ", xhr.responseText);
      console.log("Ready state changed: ", xhr.readyState); // Debug line
      console.log("HTTP status: ", xhr.status); // Debug line
      if (xhr.readyState == 4 && xhr.status == 200) {
        let response = JSON.parse(xhr.responseText);
        console.log("Received response: ", response); // Debug line
        let products = response.products;
        let productSelect = document.querySelector(
          "#id_quoteitem_set-0-product",
        );
        productSelect.innerHTML = ""; // Clear existing options

        products.forEach(function (product) {
          let option = document.createElement("option");
          option.value = product.id;
          option.text = product.name;
          productSelect.add(option);
        });
      }
    };
    xhr.send();
  };
})(django.jQuery);

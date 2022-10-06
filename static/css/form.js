function addText(price) {
  var div1 = document.getElementById("div2");
  name = `<div class="row"><div class="col-25"><label for="Price">Price</label></div><div class="col-75"><h3 type="text">${price}</h3> </div> </div>`;
  div1.innerHTML += name;

  // div1.innerHTML += '<input type="button" id="payment" value="Make Payment" />';

  // Form data
  const categorySelect = document.getElementById("subject").value;
  const projectSelect = document.getElementById("Type").value;
  const project_title = document.getElementById("fname").value;
  const pages = document.getElementById("pages").value;
  const deadline = document.getElementById("deadline").value;
  const file = document.getElementById("file").files[0];
  const instructions = document.getElementById("instructions").value;

  const btn = document.createElement("input");
  btn.type = "button";
  btn.id = "payment";
  btn.value = "Make Payment";
  div1.append(btn);

  btn.addEventListener("click", () => {
    fetch("/api/stripe/config")
      .then((result) => {
        return result.json();
      })
      .then(async (data) => {
        const stripe = Stripe(data.publicKey);

        let formData = new FormData();
        formData.append("project_title", project_title);
        formData.append("category_id", categorySelect);
        formData.append("project_id", projectSelect);
        formData.append("pages", pages);
        formData.append("deadline", deadline);
        formData.append("reference_file", file);
        formData.append("instructions", instructions);

        const sessionData = await axios.post(`/send-work`, formData);

        return stripe.redirectToCheckout({
          sessionId: sessionData.data.sessionId,
        });
      });
  });
}

// Función para calcular el total de la venta
function calcularTotal() {
    const fk_producto = document.getElementById('fk_producto').value;
    const cantidad_vendida = parseFloat(document.getElementById('cantidad_vendida').value);

    if (fk_producto && !isNaN(cantidad_vendida)) {
        fetch(`/api/productos/${fk_producto}`)
            .then(response => response.json())
            .then(producto => {
                if (producto && producto.precio) {
                    const total = producto.precio * cantidad_vendida;
                    document.getElementById('total_venta').value = total.toFixed(2);
                } else {
                    alert('Error: No se pudo obtener el precio del producto.');
                }
            })
            .catch(error => console.error('Error al calcular el total:', error));
    } else {
        alert('Por favor, selecciona un producto y una cantidad válida.');
    }
}

// Función para registrar la venta
function registrarVenta(event) {
    event.preventDefault();  // Prevenir la recarga de la página al enviar el formulario

    const fk_producto = document.getElementById('fk_producto').value;
    const fk_cliente = document.getElementById('fk_cliente').value;
    const fk_usuario = document.getElementById('fk_usuario').value;
    const cantidad_vendida = parseFloat(document.getElementById('cantidad_vendida').value);
    const total_venta = parseFloat(document.getElementById('total_venta').value);

    if (fk_producto && fk_cliente && fk_usuario && !isNaN(cantidad_vendida) && !isNaN(total_venta)) {
        const venta = {
            fk_producto,
            fk_cliente,
            fk_usuario,
            cantidad_vendida,
            total_venta
        };

        fetch('/api/ventas', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(venta),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Venta registrada con éxito');
                // Aquí puedes agregar lógica para limpiar el formulario o redirigir al usuario
                document.getElementById('registrarVenta').reset(); // Limpiar el formulario
            } else {
                alert('Error al registrar la venta: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error al registrar la venta:', error);
            alert('Ocurrió un error al registrar la venta.');
        });
    } else {
        alert('Por favor, completa todos los campos correctamente.');
    }
}

// Asociar la función registrarVenta al envío del formulario
document.getElementById('registrarVenta').addEventListener('submit', registrarVenta);

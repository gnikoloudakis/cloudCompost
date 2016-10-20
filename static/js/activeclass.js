/**
 * Created by yannis on 10/20/2016.
 */
    $(".nav ul li a").on("click", function() {
      $(".nav ul li a").removeClass("active");
      $(this).addClass("active");
    });


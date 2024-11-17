
package com.app.webnongsan.service;

import com.app.webnongsan.domain.Product;
import com.app.webnongsan.domain.response.product.ResProductDTO;
import com.app.webnongsan.repository.CategoryRepository;
import com.app.webnongsan.repository.ProductRepository;
import lombok.AllArgsConstructor;

import javax.swing.JFileChooser;

import org.apache.poi.ss.usermodel.*;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.springframework.stereotype.Service;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.io.FileOutputStream;
import java.lang.String;

@Service
@AllArgsConstructor
public class DataExportService {
    private final ProductRepository productRepository;

    public boolean lkd() {
        return false;
    }

    //    public boolean exportDataToExcel() throws IOException {
//        boolean flag = false;
//        List<Product> data = productRepository.findAll();
//        List<ResProductDTO> exportProductData = new ArrayList<>();
//        for(Product p:data){
//            ResProductDTO productInfo = new ResProductDTO();
//            productInfo.setId(p.getId());
//            productInfo.setProduct_name((p.getProductName()));
//            productInfo.setDescription(p.getDescription());
//            productInfo.setPrice(p.getPrice());
//            productInfo.setCategory(p.getCategory().getName());
//            productInfo.setUnit(p.getUnit());
//            productInfo.setRating(p.getRating());
//            productInfo.setSold(p.getSold());
//            productInfo.setQuantity(p.getQuantity());
//            exportProductData.add(productInfo);
//        }
//        Workbook workbook = new XSSFWorkbook();
//        Sheet sheet = workbook.createSheet("Sheet 1");
//
//        List<String> productColumnHeaders = List.of("ID","Phân loại", "Tên sản phẩm","Số lượng sản phẩm còn", "Giá","Đã bán","Đơn vị","Số sao","Mô tả");
//
//        Row headerRow = sheet.createRow(0);
//        for(int i=1;i<productColumnHeaders.size();i++){
//            headerRow.createCell(i).setCellValue(productColumnHeaders.get(i));
//        }
//        int rowNum = 1;
//        for (ResProductDTO p : exportProductData) {
//            Row row = sheet.createRow(rowNum++);
//            row.createCell(0).setCellValue(p.getId());
//            row.createCell(1).setCellValue(p.getCategory());
//            row.createCell(2).setCellValue(p.getProduct_name());
//            row.createCell(3).setCellValue(p.getQuantity());
//            row.createCell(4).setCellValue(p.getPrice());
//            row.createCell(5).setCellValue(p.getSold());
//            row.createCell(6).setCellValue(p.getUnit());
//            row.createCell(7).setCellValue(p.getRating());
//            row.createCell(8).setCellValue(p.getDescription());
//        }
//
//        // Tạo file tại đường dẫn chỉ định
////        File file = new File(filePath);
////        try (FileOutputStream fileOut = new FileOutputStream(file)) {
////            workbook.write(fileOut);
////        } finally {
////            workbook.close();
////        }
//
//        SimpleDateFormat dateFormat = new SimpleDateFormat("ss_mm_hh_dd_MM_yyyy");
//        String currentTime = dateFormat.format(new Date());
//        String fileName = "Product_" + currentTime + ".xlsx";
//        File file = new File(fileName);
//        try (FileOutputStream fileOut = new FileOutputStream(file)) {
//            workbook.write(fileOut);
//        } finally {
//            workbook.close();
//        }
////        File excelDir = new File("D:/Project/Java/webnongsan" + "/excel");
////
////        if (!excelDir.exists()) {
////            if (excelDir.mkdirs()) {
////            } else {
////                return flag;
////            }
////        } else {
////        }
////        File file = new File(excelDir,fileName);
////        try (FileOutputStream fileOut = new FileOutputStream(file)) {
////            workbook.write(fileOut);
////        } finally {
////            workbook.close();
////        }
//        return true;
//    }
    public byte[] exportDataToExcel() throws IOException {
        Workbook workbook = new XSSFWorkbook();
        try (ByteArrayOutputStream outputStream = new ByteArrayOutputStream()) {
            // Tạo sheet và ghi dữ liệu vào workbook
            Sheet sheet = workbook.createSheet("Products");

            // Tiêu đề cột
            List<String> headers = List.of("ID", "Category", "Name", "Quantity", "Price", "Sold", "Unit", "Rating", "Description");
            Row headerRow = sheet.createRow(0);
            for (int i = 0; i < headers.size(); i++) {
                headerRow.createCell(i).setCellValue(headers.get(i));
            }

            // Thêm dữ liệu (ví dụ)
            List<Product> products = productRepository.findAll(); // Lấy từ DB
            int rowIndex = 1;
            for (Product p : products) {
                Row row = sheet.createRow(rowIndex++);
                row.createCell(0).setCellValue(p.getId());
                row.createCell(1).setCellValue(p.getCategory().getName());
                row.createCell(2).setCellValue(p.getProductName());
                row.createCell(3).setCellValue(p.getQuantity());
                row.createCell(4).setCellValue(p.getPrice());
                row.createCell(5).setCellValue(p.getSold());
                row.createCell(6).setCellValue(p.getUnit());
                row.createCell(7).setCellValue(p.getRating());
                row.createCell(8).setCellValue(p.getDescription());
            }

            // Ghi workbook ra byte array
            workbook.write(outputStream);
            return outputStream.toByteArray();
        } finally {
            workbook.close();
        }
    }
}

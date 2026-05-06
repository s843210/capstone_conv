import React from 'react';
import {SafeAreaView, Text, View, Pressable} from 'react-native';
import {ProductDetailScreenProps} from '../types';
import {styles} from '../styles/commonStyles';

export default function ProductDetailScreen({navigation, route}: ProductDetailScreenProps) {
  const {product} = route.params;

  return (
    <SafeAreaView style={styles.page}>
      <Text style={styles.title}>{product.name}</Text>
      <View style={styles.card}>
        <Text style={styles.cardMeta}>카테고리: {product.category}</Text>
        <Text style={styles.cardMeta}>상품 코드: {product.pluCode}</Text>
        <Text style={styles.cardMeta}>
          상품 설명: 상품 신청 가능 여부는 매장 상황에 따라 달라질 수 있습니다.
        </Text>
        <Text style={styles.cardMeta}>신청 상태: 신청 가능</Text>
      </View>
      <Pressable style={styles.primaryBtn} onPress={() => navigation.navigate('RequestQty', {product})}>
        <Text style={styles.primaryBtnText}>수량 요청하기</Text>
      </Pressable>
    </SafeAreaView>
  );
}

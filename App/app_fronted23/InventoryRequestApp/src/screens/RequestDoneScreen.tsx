import React from 'react';
import {SafeAreaView, Text, View, Pressable} from 'react-native';
import {RequestDoneScreenProps} from '../types';
import {styles} from '../styles/commonStyles';

export default function RequestDoneScreen({navigation, route}: RequestDoneScreenProps) {
  const {item} = route.params;

  return (
    <SafeAreaView style={styles.page}>
      <Text style={styles.title}>요청 완료</Text>
      <Text style={styles.subtitle}>요청이 정상적으로 접수되었습니다.</Text>
      <View style={styles.card}>
        <Text style={styles.cardMeta}>상품: {item.productName}</Text>
        <Text style={styles.cardMeta}>요청 수량: {item.qty}</Text>
        <Text style={styles.cardMeta}>요청 시각: {item.createdAt}</Text>
      </View>
      <Pressable style={styles.secondaryBtn} onPress={() => navigation.navigate('MyRequests')}>
        <Text style={styles.secondaryBtnText}>내 요청 목록 확인</Text>
      </Pressable>
      <Pressable style={styles.primaryBtn} onPress={() => navigation.navigate('ProductList')}>
        <Text style={styles.primaryBtnText}>상품 목록으로</Text>
      </Pressable>
    </SafeAreaView>
  );
}
